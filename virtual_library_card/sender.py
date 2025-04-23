from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

from virtual_library_card.logging import log
from virtual_library_card.tokens import Tokens, TokenTypes

if TYPE_CHECKING:
    from virtuallibrarycard.models import CustomUser, Library


class Sender:
    @staticmethod
    def text_whitespaces_to_html(string: str) -> str:
        """Change whitespaces [space, newline] to an html format"""
        return string.replace("  ", "&nbsp;&nbsp;").replace("\n", "<br/>")

    @staticmethod
    def send_user_welcome(
        library: Library,
        user: CustomUser,
        card_number: str | None = None,
    ):
        """Send out a welcome email which has two optional parts
        - User welcome for a new card
        - Email verification for an unverified email

        The user generated top and bottom text is first sanitized,
        then it's whitespaces are formatted to HTML

        :param library: The library of the patron
        :param user: The patron
        :param card_number: The card number of a newly created card"""
        to = user.email
        host = settings.ROOT_URL
        has_welcome = card_number is not None
        log.debug(f"send_user_welcome to: {to}, from: {settings.DEFAULT_FROM_EMAIL}")

        try:
            verification_link = None
            if not user.email_verified:
                token = Tokens.generate(TokenTypes.EMAIL_VERIFICATION, email=user.email)
                verification_link = (
                    f"{host}{reverse('email_token_verify')}?token={token}"
                )

            subject = _(f"{library.name}: Welcome to the Palace App")
            html_message = render_to_string(
                "email/welcome_user.html",
                {
                    "card_number": card_number,
                    "login_url": Sender._get_absolute_login_url(library.identifier),
                    "library": library,
                    "verification_link": verification_link,
                    "has_welcome": has_welcome,
                    "has_verification": not user.email_verified,
                    "custom_top_text": Sender.text_whitespaces_to_html(
                        strip_tags(library.customization.welcome_email_top_text or "")
                    ),
                    "custom_bottom_text": Sender.text_whitespaces_to_html(
                        strip_tags(
                            library.customization.welcome_email_bottom_text or ""
                        )
                    ),
                },
            )
            plain_message = strip_tags(html_message)
            msg = EmailMultiAlternatives(
                subject, plain_message, settings.DEFAULT_FROM_EMAIL, to=[to]
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send()
        except Exception as e:
            log.error(f"send email error {e}")

    @staticmethod
    def send_bulk_upload_report(email: str, library: Library, report_file: str):
        subject = _(
            "Bulk Upload Results | %(library_name)s" % dict(library_name=library.name)
        )
        html_string = render_to_string(
            "email/csv_upload_report.html", {"library_name": library.name}
        )
        plain_message = strip_tags(html_string)
        msg = EmailMultiAlternatives(
            subject, plain_message, settings.DEFAULT_FROM_EMAIL, to=[email]
        )
        msg.attach_alternative(html_string, "text/html")
        msg.attach_file(report_file)
        msg.send()

    @staticmethod
    def _get_absolute_login_url(library_identifier):
        url = settings.ROOT_URL + reverse("login") + library_identifier + "/"
        return url
