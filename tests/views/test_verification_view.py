from types import LambdaType
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm
from django.core import mail
from django.urls import reverse
from parameterized import parameterized

from tests.base import BaseUnitTest
from virtual_library_card.tokens import Tokens, TokenTypes


class TestEmailTokenVerificationViews(BaseUnitTest):
    def test_verification(self):
        user = self.create_user(self._default_library, email_verified=False)
        assert user.email_verified == False

        token = Tokens.generate(TokenTypes.EMAIL_VERIFICATION, email=user.email)
        response = self.client.get("/verify/email", dict(token=token), follow=False)

        assert response.status_code == 200
        self.assertTemplateUsed(response, "verification/email_success.html")

        user.refresh_from_db()
        assert user.email_verified == True

    @parameterized.expand(
        [
            ("something", lambda u: dict(email=u.email)),
            ("something", lambda u: dict(email="notemail")),
            (TokenTypes.EMAIL_VERIFICATION, lambda u: dict(email="notemail")),
            (TokenTypes.EMAIL_VERIFICATION, lambda u: dict()),
        ]
    )
    def test_bad_token_data(self, token_type: str, data_gen: LambdaType):
        user = self.create_user(
            self._default_library, is_active=False, email_verified=False
        )

        token = Tokens.generate(token_type, **data_gen(user))
        response = self.client.get("/verify/email", dict(token=token), follow=False)

        assert response.status_code == 302
        assert response.get("location") == reverse("email_token_error")
        user.refresh_from_db()
        assert user.is_active == False
        assert user.email_verified == False

    def test_expired_token(self):
        user = self.create_user(self._default_library, email_verified=False)
        token = Tokens.generate(
            TokenTypes.EMAIL_VERIFICATION,
            expires_in_days=-1,
            email=user.email,
        )
        response = self.client.get("/verify/email", dict(token=token), follow=False)
        assert response.status_code == 302
        assert response.get("location") == reverse("email_token_resend")
        assert "verification_email_address" in response.wsgi_request.session

        token = Tokens.generate(
            TokenTypes.EMAIL_VERIFICATION,
            expires_in_days=-1,
            email="wrongemail",
        )
        response = self.client.get("/verify/email", dict(token=token), follow=False)
        assert response.status_code == 302
        assert response.get("location") == reverse("email_token_error")

    def test_expired_already_verified(self):
        user = self._default_user
        token = Tokens.generate(
            TokenTypes.EMAIL_VERIFICATION,
            expires_in_days=-1,
            email=self._default_user.email,
        )

        response = self.client.get("/verify/email", dict(token=token), follow=False)
        assert response.status_code == 200

    def test_resend_post(self):
        session = self.client.session
        session["verification_email_address"] = self._default_user.email
        session.save()
        response = self.client.post("/verify/email/resend")

        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject.startswith(
            f"{self._default_library.name}: Welcome"
        )

        # session will be popped
        assert self.client.session.get("verification_email_address") == None
        mail.outbox.pop()
        response = self.client.post("/verify/email/resend")

        assert len(mail.outbox) == 0
        assert "?success=f" in response.get("location")

    def test_no_password_form(self):
        user = self._default_user
        user.password = ""
        user.save()
        token = Tokens.generate(
            TokenTypes.EMAIL_VERIFICATION, expires_in_days=1, email=user.email
        )
        response = self.client.get("/verify/email", dict(token=token))
        assert "form" in response.context_data
        assert type(response.context_data["form"]) == SetPasswordForm

    def test_password_set_post(self):
        """Is the password set on a post to the verification form
        This sounds funny, but the password set form is on the email verification page
        because a user may be created without a password, and will subsequently require a password to log in
        """
        user = self._default_user
        token = Tokens.generate(
            TokenTypes.EMAIL_VERIFICATION, expires_in_days=1, email=user.email
        )
        response = self.client.post(
            f"/verify/email?token={token}",
            data=dict(new_password1="test123456", new_password2="test123456"),
        )

        assert response.status_code == 200
        assert response.context_data.get("did_set_password") == True

        user.refresh_from_db()
        assert user.check_password("test123456")

    def test_app_link_redirect(self):
        user = self.create_user(self._default_library)
        card = self.create_library_card(user, user.library)
        token = Tokens.generate(
            TokenTypes.EMAIL_VERIFICATION, expires_in_days=1, email=user.email
        )
        with patch(
            "virtuallibrarycard.views.views_verification.FirebaseDynamicLinksAPI"
        ) as api:
            api().create_signup_short_link.return_value = "test-short-link"
            self._default_library.uuid = "test-uuid"
            self._default_library.save()

            # Happy path
            response = self.client.get("/verify/email", dict(token=token))
            assert "redirect_link" in response.context_data
            assert "test-short-link" == response.context_data["redirect_link"]

            # Remove the link settings
            dl_settings = settings.DYNAMIC_LINKS
            delattr(settings, "DYNAMIC_LINKS")
            response = self.client.get("/verify/email", dict(token=token))
            assert "redirect_link" not in response.context_data

            # Reset the config
            settings.DYNAMIC_LINKS = dl_settings

            # User without a password still needs some setup
            user.password = ""
            user.save()
            response = self.client.get("/verify/email", dict(token=token))
            assert "redirect_link" not in response.context_data

            # reset password
            user.set_password("password")
            user.save()

            # No card available for the redirect
            card.delete()
            response = self.client.get("/verify/email", dict(token=token))
            assert "redirect_link" not in response.context_data

            # Recreate the card, we should still be working
            card = self.create_library_card(user, user.library)
            response = self.client.get("/verify/email", dict(token=token))
            assert "redirect_link" in response.context_data

            # No UUID provided, no link possible
            self._default_library.uuid = ""
            self._default_library.save()
            response = self.client.get("/verify/email", dict(token=token))
            assert "redirect_link" not in response.context_data
