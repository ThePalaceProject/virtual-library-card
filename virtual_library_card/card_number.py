import random

from django.db import transaction

import virtuallibrarycard.models
from virtual_library_card.logging import log
from virtual_library_card.profanity import ProfanityWordList


class CardNumber:
    NUMBER_GENERATION_RETRIES = 100
    # Length of the entire card number
    CARD_NUMBER_LENGTH = 14
    # Minimum length the random part should be
    MIN_RANDOM_LENGTH = 4
    # What characters are allowed in the random sequence, 0-9 A-Z
    ALLOWED_CHARACTERS = [str(i) for i in range(10)] + [
        chr(i) for i in range(ord("A"), ord("Z") + 1)
    ]

    @classmethod
    def _generate_random_characters(cls, length: int):
        return "".join(random.choices(cls.ALLOWED_CHARACTERS, k=length))

    @staticmethod
    def generate_card_number(library_card):
        if library_card.library is None:
            return 0

        # Length of randomly generated characters
        serialized_length = CardNumber.CARD_NUMBER_LENGTH - len(
            library_card.library.prefix
        )
        # Must be of some useful length
        if serialized_length < CardNumber.MIN_RANDOM_LENGTH:
            raise ValueError(
                f"Card number length cannot be < {CardNumber.MIN_RANDOM_LENGTH} characters, your library prefix is too long."
            )

        exists = False
        with transaction.atomic():
            # failsafe number of tries before failing the generation
            for _ in range(CardNumber.NUMBER_GENERATION_RETRIES):
                random_chars = CardNumber._generate_random_characters(serialized_length)
                number = f"{library_card.library.prefix}{random_chars}"

                # Test for profane words
                if ProfanityWordList.contains_profanity(number):
                    log.info(f"Discarding {number}: Contains profanity.")
                    continue

                # Test the availability of this number, else retry
                exists = virtuallibrarycard.models.LibraryCard.objects.filter(
                    library=library_card.library, number=number
                ).exists()
                if exists:
                    log.info(f"Discarding {number}: Card number already exists.")
                    continue

                # Number is available
                library_card.number = number
                break
            else:
                log.error(
                    f"Could not create a unique card number. Last tried: {number}"
                )

        # Raise an error that we failed, after exiting the atomic transaction.
        if exists:
            raise RuntimeError("Could not create a unique card number")
