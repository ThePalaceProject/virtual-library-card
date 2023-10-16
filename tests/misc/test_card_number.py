from unittest import mock

import pytest

from tests.base import BaseUnitTest
from virtual_library_card.card_number import CardNumber
from virtuallibrarycard.models import LibraryCard


class TestCardNumber(BaseUnitTest):
    def test_generate_card_number(self):
        with mock.patch("virtual_library_card.card_number.random") as mock_random:
            # Card with no library
            lc = LibraryCard()
            assert CardNumber.generate_card_number(lc) == 0
            assert lc.number == None

            mock_random.randint.return_value = 1234567
            lc1 = LibraryCard(library=self._default_library)
            CardNumber.generate_card_number(lc1)
            # magic number 14
            remaining = (
                14 - len(self._default_library.prefix) - len(str(mock_random.randint()))
            )
            assert lc1.number == self._default_library.prefix + "0" * remaining + str(
                mock_random.randint()
            )

            # More than 14 chars prefix fails
            self._default_library.prefix = "p" * 20
            with pytest.raises(ValueError, match="your library prefix is too long."):
                CardNumber.generate_card_number(lc1)

    def test_generate_unique_card_number(self):
        with mock.patch("virtual_library_card.card_number.random") as mock_random:
            library = self.create_library(prefix="AA")
            pattern = "AA{:0" + str(14 - len(library.prefix)) + "d}"
            lc = self.create_library_card(
                self._default_user, library, number=pattern.format(11111111)
            )
            number1 = lc.number
            mock_random.randint.side_effect = [11111111, 22222222]
            CardNumber.generate_card_number(lc)
            # The first random number will be ignored due to duplicate constraints
            assert lc.number != number1
            assert lc.number == "AA000022222222"

            # Now retry MAX times till you fail, always return the same number
            mock_random.randint.side_effect = None
            mock_random.randint.return_value = 11111111
            with pytest.raises(RuntimeError) as ex:
                CardNumber.generate_card_number(lc)

            assert ex.match("Could not create a unique card number")
