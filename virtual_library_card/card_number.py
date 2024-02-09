from django.conf import settings
from django.db import transaction
from sequences import get_last_value, get_next_value

import VirtualLibraryCard.models
from virtual_library_card.sender import Sender


class CardNumber:
    @staticmethod
    def _generate_number_from_sequence(library):
        next_val = get_next_value(
            CardNumber._card_number_sequence_name(library),
            CardNumber._get_sequence_init_value(library, library.sequence_start_number),
        )
        print(next_val, "_generate_number_from_sequence next_val")
        if library.sequence_down:
            print("library.sequence_down", library.sequence_down)
            next_val = library.sequence_start_number - next_val
            if library.sequence_end_number is not None:
                next_val += library.sequence_end_number
        must_send_alert = (
            next_val - library.sequence_start_number < settings.CARD_NUMBERS_LIMIT_ALERT
        )
        print("must_send_alert", must_send_alert)
        if must_send_alert:
            try:
                admin_users = VirtualLibraryCard.models.CustomUser.library_admins(
                    library
                )
                super_users = VirtualLibraryCard.models.CustomUser.super_users()
                Sender.send_admin_card_numbers_alert(library, admin_users, super_users)
            except Exception as e:
                print("send_admin_card_numbers_alert error ", e)

        return next_val

    # @staticmethod
    # def _get_sequence_max(library):
    #     if library.sequence_end_number is None:
    #         return sys.maxsize
    #     return library.sequence_end_number

    @staticmethod
    def reset_sequence(library):
        print("----reset_sequence")
        with transaction.atomic():
            last_value: int = get_last_value(
                CardNumber._card_number_sequence_name(library)
            )
            print("reset_sequence last_value", last_value)
            if last_value is None:
                return

            sequence_start_number: int = library.sequence_start_number
            print(sequence_start_number, "self.sequence_start_number")
            print(last_value, "last_value")

            if library.sequence_down is False and last_value < sequence_start_number:
                while last_value < sequence_start_number:
                    last_value = get_next_value(
                        CardNumber._card_number_sequence_name(library)
                    )
                return

            init_val = CardNumber._get_sequence_init_value(
                library, sequence_start_number
            )
            print("init_val ", init_val)
            get_next_value(
                CardNumber._card_number_sequence_name(library), init_val, last_value
            )

    @staticmethod
    def _get_sequence_init_value(library, sequence_start_number):
        init_val = sequence_start_number
        if library.sequence_down:
            init_val = (
                0
                if library.sequence_end_number is None
                else library.sequence_end_number
            )
        return init_val

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
        serialized_length = 14 - len(library_card.library.prefix)

        with transaction.atomic():
            print(serialized_length.__str__(), "serialized_length.__str__()")
            pattern = "{:0" + serialized_length.__str__() + "d}"
            print(pattern, "pattern")
            suffix_number = pattern.format(
                CardNumber._generate_number_from_sequence(library_card.library)
            )
            print("suffix_number", suffix_number)
            library_card.number = library_card.library.prefix + suffix_number
            print("library_card.number", library_card.number)

    @staticmethod
    def _card_number_sequence_name(library):
        return "library_card_number_" + library.prefix
