from unittest import mock

import pytest
from django.conf import settings
from parameterized import param, parameterized
from sequences import get_last_value

from tests.base import BaseUnitTest
from virtual_library_card.card_number import CardNumber
from VirtualLibraryCard.models import LibraryCard


class TestCardNumber(BaseUnitTest):
    @parameterized.expand(
        [
            param(limit=100, should_alert=[False, False, False]),
            param(limit=1, should_alert=[True, True, True]),
            param(limit=2, should_alert=[False, True, True]),
            param(limit=3, should_alert=[False, False, True]),
        ]
    )
    @mock.patch("virtual_library_card.card_number.Sender")
    def test_generate_number_from_sequence(
        self, mock_sender: mock.MagicMock, limit, should_alert
    ):
        def assert_alerts(alert):
            """Assert and reset the mock sender"""
            assert mock_sender.send_admin_card_numbers_alert.call_count == (
                0 if not alert else 1
            )
            if alert:
                mock_sender.send_admin_card_numbers_alert.call_args[0][
                    0
                ] == self._default_library
            mock_sender.reset_mock()

        settings.CARD_NUMBERS_LIMIT_ALERT = limit

        num = CardNumber._generate_number_from_sequence(self._default_library)
        assert num == 1
        assert_alerts(should_alert.pop(0))

        # Counting down
        self._default_library.sequence_down = True
        num = CardNumber._generate_number_from_sequence(self._default_library)
        assert num == -2  # instead of 2
        assert_alerts(should_alert.pop(0))

        # Counting down from a limit
        self._default_library.sequence_end_number = 100
        num = CardNumber._generate_number_from_sequence(self._default_library)
        assert num == 100 - 3  # counting down from 100 now
        assert_alerts(should_alert.pop(0))

    def test_reset_sequence(self):
        CardNumber._generate_number_from_sequence(self._default_library)
        num = get_last_value(
            CardNumber._card_number_sequence_name(self._default_library)
        )
        assert num == 1

        CardNumber.reset_sequence(self._default_library)
        num = get_last_value(
            CardNumber._card_number_sequence_name(self._default_library)
        )
        assert num == 0

        self._default_library.sequence_start_number = 10
        CardNumber.reset_sequence(self._default_library)
        num = get_last_value(
            CardNumber._card_number_sequence_name(self._default_library)
        )
        assert num == 10

        self._default_library.sequence_down = True
        CardNumber.reset_sequence(self._default_library)
        num = get_last_value(
            CardNumber._card_number_sequence_name(self._default_library)
        )
        assert num == 0

        self._default_library.sequence_end_number = 100
        self._default_library.sequence_start_number = 0
        # Is this a bug? Why is this raised??
        with pytest.raises(AssertionError):
            CardNumber.reset_sequence(self._default_library)

    def test_get_sequence_init_value(self):
        assert CardNumber._get_sequence_init_value(self._default_library, 0) == 0

        self._default_library.sequence_down = True
        assert CardNumber._get_sequence_init_value(self._default_library, 0) == 0

        self._default_library.sequence_end_number = 100
        assert CardNumber._get_sequence_init_value(self._default_library, 0) == 100

    def test_generate_card_number(self):
        # Card with no library
        lc = LibraryCard()
        assert CardNumber.generate_card_number(lc) == 0
        assert lc.number == None

        lc1 = LibraryCard(library=self._default_library)
        CardNumber.generate_card_number(lc1)
        # magic number 14
        remaining = 14 - len(self._default_library.prefix)
        assert lc1.number == self._default_library.prefix + "0" * (remaining - 1) + "1"

        # nuber overwrites
        CardNumber.generate_card_number(lc1)
        assert lc1.number == self._default_library.prefix + "0" * (remaining - 1) + "2"

        # More than 14 chars prefix fails
        self._default_library.prefix = "p" * 20
        with pytest.raises(ValueError, match="Invalid format specifier"):
            CardNumber.generate_card_number(lc1)

    def test_generate_unique_card_number(self):
        library = self.create_library(prefix="AA")
        pattern = "AA{:0" + str(14 - len(library.prefix)) + "d}"
        lc = self.create_library_card(
            self._default_user, library, number=pattern.format(0)
        )
        number1 = lc.number
        CardNumber.generate_card_number(lc)
        assert lc.number != number1
        assert lc.number[-1] == "1"

        # generate 3 more cards
        for i in range(2, 5):
            self.create_library_card(
                self._default_user, library, number=pattern.format(i)
            )

        # This should now be 5
        CardNumber.generate_card_number(lc)
        assert lc.number[-1] == "5"

        # Now retry MAX times till you fail, sequence should advance after failure
        for i in range(6, 6 + CardNumber.NUMBER_GENERATION_RETRIES):
            self.create_library_card(
                self._default_user, library, number=pattern.format(i)
            )

        with pytest.raises(RuntimeError) as ex:
            CardNumber.generate_card_number(lc)

        assert ex.match("Could not create a unique card number")
        # Ensure the sequence generator has moved forward before failing
        assert (
            CardNumber._generate_number_from_sequence(lc.library)
            == CardNumber.NUMBER_GENERATION_RETRIES + 6
        )
