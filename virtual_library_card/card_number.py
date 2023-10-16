import random

from django.db import transaction

import virtuallibrarycard.models
from virtual_library_card.logging import log


class CardNumber:
    NUMBER_GENERATION_RETRIES = 100
    # Length of the entire card number
    CARD_NUMBER_LENGTH = 14
    # Minimum length the numeric part should be
    MIN_NUMERIC_LENGTH = 4

    @staticmethod
    def _generate_random_number(length: int, min_length=1) -> int:
        max_int = int("9" * length)
        min_int = pow(10, min_length - 1)
        return random.randint(min_int, max_int)

    @staticmethod
    def generate_card_number(library_card):
        if library_card.library is None:
            return 0

        """Library card number = [Library prefix]-[serialized part]
                               (e.g prefix - #### - ########## or 0123-0123456789)
                               The prefix can be variable length.
                               The second part I serialized.
                               The total barcode length (prefix and serialized part) is 14 digits)
                                   """
        serialized_length = CardNumber.CARD_NUMBER_LENGTH - len(
            library_card.library.prefix
        )
        if serialized_length < CardNumber.MIN_NUMERIC_LENGTH:
            raise ValueError(
                f"Card number length cannot be < {CardNumber.MIN_NUMERIC_LENGTH}, your library prefix is too long."
            )

        exists = False
        with transaction.atomic():
            # failsafe number of tries before failing the generation
            for _ in range(CardNumber.NUMBER_GENERATION_RETRIES):
                pattern = "{:0" + serialized_length.__str__() + "d}"
                suffix_number = pattern.format(
                    CardNumber._generate_random_number(
                        serialized_length, min_length=serialized_length // 2
                    )
                )
                # we don't want too many zeros in the number, it looks shabby
                if suffix_number.count("0") > serialized_length // 3:
                    log.info(
                        f"Discarding random number {suffix_number}: Too many zeros."
                    )
                    continue
                number = library_card.library.prefix + suffix_number
                # Test the availability of this number, else retry
                exists = virtuallibrarycard.models.LibraryCard.objects.filter(
                    library=library_card.library, number=number
                ).exists()
                if exists:
                    log.info(
                        f"Discarding random number {suffix_number}: Card number already exists."
                    )
                    continue
                # Number is available
                library_card.number = number
                break
            else:
                log.error(
                    f"Could not create a unique card number. Last tried: {suffix_number}"
                )

        # Raise an error that we failed, after exiting the atomic transaction.
        if exists:
            raise RuntimeError("Could not create a unique card number")

    @staticmethod
    def _card_number_sequence_name(library):
        return "library_card_number_" + library.prefix
