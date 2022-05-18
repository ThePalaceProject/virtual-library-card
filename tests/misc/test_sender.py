from unittest import mock

from django.conf import settings

from tests.base import BaseUnitTest
from virtual_library_card.sender import Sender


class TestSender(BaseUnitTest):
    @mock.patch("virtual_library_card.sender.EmailMultiAlternatives")
    @mock.patch("virtual_library_card.sender.render_to_string")
    def test_send_admin_card_numbers_alert(
        self, mock_render: mock.MagicMock, mock_email: mock.MagicMock
    ):
        library = self._default_library
        superuser = self.create_user(library)
        admin = self.create_user(library)

        return_value = "returnvalue"
        mock_render.return_value = return_value

        Sender.send_admin_card_numbers_alert(library, [admin], [superuser])

        assert mock_render.call_count == 1
        assert mock_render.call_args[0] == (
            "email/number_sequence_alert.html",
            {
                "library_name": library.name,
                "identifier": library.identifier,
                "logo_url": library.logo.url,
                "login_url": Sender._get_absolute_login_url(library.identifier),
            },
        )

        assert mock_email.call_count == 1
        assert mock_email.call_args[0] == (
            f"{library.name} cards numbers | The limit will be reached soon",
            return_value,
            settings.DEFAULT_FROM_EMAIL,
        )
        assert mock_email.call_args_list[0].kwargs == dict(
            to=[admin.email],
            cc=[superuser.email],
        )

        assert mock_email().attach_alternative.call_count == 1
        assert mock_email().attach_alternative.call_args[0] == (
            return_value,
            "text/html",
        )

        assert mock_email().send.call_count == 1

    @mock.patch("virtual_library_card.sender.EmailMultiAlternatives")
    @mock.patch("virtual_library_card.sender.render_to_string")
    def test_send_user_welcome(
        self, mock_render: mock.MagicMock, mock_email: mock.MagicMock
    ):
        library = self._default_library
        user = self._default_user
        card = self._default_card

        render_string = "mockrender"
        mock_render.return_value = render_string

        Sender.send_user_welcome(library, user, card)
        mock_render.call_count == 1
        mock_render.call_args[0] == (
            "email/welcome_user.html",
            {
                "library_name": library.name,
                "identifier": library.identifier,
                "card_number": card.number,
                "login_url": Sender._get_absolute_login_url(library.identifier),
            },
        )

        assert mock_email.call_count == 1
        assert mock_email.call_args_list[0].args == (
            f"{library.name} | Welcome",
            render_string,
            settings.DEFAULT_FROM_EMAIL,
        )
        assert mock_email.call_args_list[0].kwargs == dict(to=[user.email])

        assert mock_email().attach_alternative.call_count == 1
        assert mock_email().attach_alternative.call_args[0] == (
            render_string,
            "text/html",
        )
        assert mock_email().send.call_count == 1

    def test_get_absolute_login_url(self):
        url = Sender._get_absolute_login_url(self._default_library.identifier)
        assert (
            url
            == f"{settings.ROOT_URL}/accounts/login/{self._default_library.identifier}/"
        )
