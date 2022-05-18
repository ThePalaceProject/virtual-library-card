from unittest import mock

import pytest
from django.conf import settings
from sequences import get_last_value

from tests.base import BaseUnitTest
from virtual_library_card.card_number import CardNumber
from VirtualLibraryCard.models import LibraryCard


class TestCardNumber(BaseUnitTest):
    @mock.patch("virtual_library_card.card_number.Sender")
    def test_generate_number_from_sequence(self, mock_sender: mock.MagicMock):

        settings.CARD_NUMBERS_LIMIT_ALERT = 100
        num = CardNumber._generate_number_from_sequence(self._default_library)
        assert num == 1

        # Assert the limit was reached
        # This seems like the code is wrong in the function
        # why would we raise an email for every card created
        # up to a certain limit
        mock_sender.send_admin_card_numbers_alert.assert_called_once()
        mock_sender.send_admin_card_numbers_alert.call_args[0][
            0
        ] == self._default_library

        # Counting down
        mock_sender.send_admin_card_numbers_alert = mock.MagicMock()  # reset
        self._default_library.sequence_down = True
        num = CardNumber._generate_number_from_sequence(self._default_library)
        assert num == -2  # instead of 2
        mock_sender.send_admin_card_numbers_alert.assert_called_once()
        mock_sender.send_admin_card_numbers_alert.call_args[0][
            0
        ] == self._default_library

        # Counting down from a limit
        mock_sender.send_admin_card_numbers_alert = mock.MagicMock()  # reset
        self._default_library.sequence_end_number = 100
        num = CardNumber._generate_number_from_sequence(self._default_library)
        assert num == 97  # counting down from 100 now
        mock_sender.send_admin_card_numbers_alert.assert_called_once()
        mock_sender.send_admin_card_numbers_alert.call_args[0][
            0
        ] == self._default_library

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
