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
    from VirtualLibraryCard.models import Library


class Sender:
    @staticmethod
    def send_admin_card_numbers_alert(library, library_admin_users, super_users):
        # Send library_alert
        to = [u.email for u in library_admin_users]
        cc = [u.email for u in super_users]

        subject = _(
            "%(library_name)s cards numbers | The limit will be reached soon"
            % {"library_name": library.name}
        )
        html_message = render_to_string(
            "email/number_sequence_alert.html",
            {
                "library_name": library.name,
                "identifier": library.identifier,
                "logo_url": library.logo.url,
                "login_url": Sender._get_absolute_login_url(library.identifier),
            },
        )
        plain_message = strip_tags(html_message)
        msg = EmailMultiAlternatives(
            subject, plain_message, settings.DEFAULT_FROM_EMAIL, to=to, cc=cc
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()

    @staticmethod
    def send_user_welcome(library, user, card_number):
        to = user.email

        log.debug(f"send_user_welcome to: {to}, from: {settings.DEFAULT_FROM_EMAIL}")
        try:
            subject = _("%(library_name)s | Welcome" % {"library_name": library.name})
            html_message = render_to_string(
                "email/welcome_user.html",
                {
                    "identifier": library.identifier,
                    "card_number": card_number,
                    "login_url": Sender._get_absolute_login_url(library.identifier),
                    "library": library,
                    "user_email_verified": user.email_verified,
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
    def send_email_verification(library, user):
        try:
            host = settings.ROOT_URL
            subject = _(
                "Verify your email address %(name)s" % {"name": user.first_name}
            )
            token = Tokens.generate(TokenTypes.EMAIL_VERIFICATION, email=user.email)
            html_string = render_to_string(
                "email/email_verification.html",
                {
                    "link": f"{host}{reverse('email_token_verify')}?token={token}",
                    "library_name": library.name,
                },
            )
            plain_message = strip_tags(html_string)
            msg = EmailMultiAlternatives(
                subject, plain_message, settings.DEFAULT_FROM_EMAIL, to=[user.email]
            )
            msg.attach_alternative(html_string, "text/html")
            msg.send()
        except Exception as e:
            log.exception(f"Verification Email: Could not email {user.email}")

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
