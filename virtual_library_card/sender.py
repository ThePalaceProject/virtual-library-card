from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

from virtual_library_card.logging import log


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
                    "library_name": library.name,
                    "identifier": library.identifier,
                    "card_number": card_number,
                    "login_url": Sender._get_absolute_login_url(library.identifier),
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
    def _get_absolute_login_url(library_identifier):
        url = settings.ROOT_URL + reverse("login") + library_identifier + "/"
        return url
