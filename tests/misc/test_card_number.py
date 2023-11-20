from unittest import mock

import pytest

from tests.base import BaseUnitTest
from virtual_library_card.card_number import CardNumber
from virtual_library_card.profanity import ProfanityWordList
from virtuallibrarycard.models import LibraryCard


class TestCardNumber(BaseUnitTest):
    def test_allowed_characters(self):
        assert len(CardNumber.ALLOWED_CHARACTERS) == 36
        assert CardNumber.ALLOWED_CHARACTERS[0] == "0"
        assert CardNumber.ALLOWED_CHARACTERS[-1] == "Z"

    def test_generate_card_number(self):
        lc = LibraryCard(library=self._default_library)
        CardNumber.generate_card_number(lc)
        assert lc.number is not None
        assert len(lc.number) == 14

        with mock.patch("virtual_library_card.card_number.random") as mock_random:
            # Card with no library
            lc = LibraryCard()
            assert CardNumber.generate_card_number(lc) == 0
            assert lc.number == None

            mock_random.choices.return_value = ["1", "2", "3", "4"]
            lc1 = LibraryCard(library=self._default_library)
            CardNumber.generate_card_number(lc1)
            assert lc1.number == f"{self._default_library.prefix}1234"

            # More than 14 chars prefix fails
            self._default_library.prefix = "p" * 20
            with pytest.raises(ValueError, match="your library prefix is too long."):
                CardNumber.generate_card_number(lc1)

    def test_generate_unique_card_number(self):
        with mock.patch("virtual_library_card.card_number.random") as mock_random:
            library = self.create_library(prefix="AA")
            pattern = "AA{}"
            lc = self.create_library_card(
                self._default_user, library, number=pattern.format(11111111)
            )
            number1 = lc.number
            mock_random.choices.side_effect = [["1"] * 8, ["2"] * 8]
            CardNumber.generate_card_number(lc)
            # The first random number will be ignored due to duplicate constraints
            assert lc.number != number1
            assert lc.number == "AA22222222"

            # Now retry MAX times till you fail, always return the same number
            mock_random.choices.side_effect = None
            mock_random.choices.return_value = ["1"] * 8
            with pytest.raises(RuntimeError) as ex:
                CardNumber.generate_card_number(lc)

            assert ex.match("Could not create a unique card number")

    def test_generate_without_profanity(self):
        with mock.patch("virtual_library_card.card_number.random") as mock_random:
            card = self.create_library_card(self._default_user, self._default_library)
            ProfanityWordList._generate_wordlist(custom_words=["bard"])
            mock_random.choices.side_effect = [
                ["b", "4", "r", "d"],
                ["1", "2", "3", "4"],
            ]
            CardNumber.generate_card_number(card)
            # Bard should get disarded and 1234 used
            assert card.number.endswith("1234")
