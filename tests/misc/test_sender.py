from unittest import mock

from django.conf import settings
from django.core import mail
from django.urls import reverse

from tests.base import BaseUnitTest
from virtual_library_card.sender import Sender


class TestSender(BaseUnitTest):
    @mock.patch("virtual_library_card.sender.EmailMultiAlternatives")
    @mock.patch("virtual_library_card.sender.render_to_string")
    @mock.patch("virtual_library_card.sender.Tokens")
    def test_send_user_welcome(
        self,
        mock_tokens: mock.MagicMock,
        mock_render: mock.MagicMock,
        mock_email: mock.MagicMock,
    ):
        library = self._default_library
        user = self._default_user
        card = self._default_card

        library.customization.welcome_email_top_text = "Welcome user top text"
        library.customization.welcome_email_bottom_text = "Welcome user bottom text"

        render_string = "mockrender"
        mock_render.return_value = render_string

        Sender.send_user_welcome(library, user, card.number)
        token_url = f"{settings.ROOT_URL}{reverse('email_token_verify')}?token="

        assert mock_render.call_count == 1
        assert mock_render.call_args[0] == (
            "email/welcome_user.html",
            {
                "card_number": card.number,
                "login_url": Sender._get_absolute_login_url(library.identifier),
                "reset_url": Sender._get_absolute_reset_url(library.identifier),
                "library": library,
                "verification_link": None,
                "has_verification": False,
                "has_welcome": True,
                "custom_top_text": library.customization.welcome_email_top_text,
                "custom_bottom_text": library.customization.welcome_email_bottom_text,
            },
        )

        assert mock_email.call_count == 1
        assert mock_email.call_args_list[0].args == (
            f"{library.name}: Welcome to the Palace App",
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

        mock_render.reset_mock()
        user.email_verified = False
        mock_tokens.generate.return_value = "Generated"
        Sender.send_user_welcome(library, user)
        assert mock_render.call_args[0] == (
            "email/welcome_user.html",
            {
                "card_number": None,
                "login_url": Sender._get_absolute_login_url(library.identifier),
                "reset_url": Sender._get_absolute_reset_url(library.identifier),
                "library": library,
                "verification_link": token_url + "Generated",
                "has_verification": True,
                "has_welcome": False,
                "custom_top_text": library.customization.welcome_email_top_text,
                "custom_bottom_text": library.customization.welcome_email_bottom_text,
            },
        )

    def test_send_user_welcome_none_custom_text(self):
        """In case we have nonetype custom text
        the email should not contain "None" strings
        """
        library = self._default_library
        user = self._default_user
        card = self._default_card

        library.customization.welcome_email_top_text = None
        library.customization.welcome_email_bottom_text = None

        Sender.send_user_welcome(library, user, card.number)

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]

        assert "None" not in sent.body

    def test_get_absolute_login_url(self):
        url = Sender._get_absolute_login_url(self._default_library.identifier)
        assert (
            url
            == f"{settings.ROOT_URL}/accounts/login/{self._default_library.identifier}/"
        )

    def test_get_absolute_reset_url(self):
        url = Sender._get_absolute_reset_url(self._default_library.identifier)
        assert (
            url
            == f"{settings.ROOT_URL}/account/reset-password/{self._default_library.identifier}/"
        )

    def test_libary_email_configurables(self):
        library = self._default_library
        user = self._default_user

        library.barcode_text = "totally not a number"
        library.pin_text = "very special secret"

        Sender.send_user_welcome(library, user, "12345")
        assert len(mail.outbox) == 1
        msg = mail.outbox[0]

        # New text is present
        assert "totally not a number: 12345" in msg.body
        assert "very special secret:" in msg.body
        # Original text is not present
        assert "card number:" not in msg.body.lower()
        assert "password:" not in msg.body.lower()

    def test_libary_email_text_formatting(self):
        library = self._default_library
        user = self._default_user

        library.customization.welcome_email_top_text = "Welcome user top text!"
        library.customization.welcome_email_bottom_text = "Welcome user bottom text!"

        Sender.send_user_welcome(library, user, "12345")
        [msg] = mail.outbox

        assert (
            msg.body
            == f"""
Hello,

Welcome user top text!

Thank you for joining Default.

Your login details are below:

barcode: 12345
pin: use the password you created when you signed up for a card

Save this email to retain your login information. If you have forgotten your password, please visit {Sender._get_absolute_reset_url(self._default_library.identifier)} OR click "Forgot your password?" on the Settings - Libraries screen in the Palace app.

You are receiving this message because someone used this email address to request a library card for Default. If you were not expecting this to happen, please ignore this message.

Welcome user bottom text!

Happy Reading,
The Palace Team and Default
        """.strip()
        )

    def test_whitespaces_to_html(self):
        string = """A\n\nB    C D   E  \nF"""

        assert (
            "A<br/><br/>B&nbsp;&nbsp;&nbsp;&nbsp;C D&nbsp;&nbsp; E&nbsp;&nbsp;<br/>F"
            == Sender.text_whitespaces_to_html(string)
        )
