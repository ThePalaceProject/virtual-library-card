from types import LambdaType

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
        assert mail.outbox[0].subject.startswith("Verify your email address")

        # session will be popped
        assert self.client.session.get("verification_email_address") == None
        mail.outbox.pop()
        response = self.client.post("/verify/email/resend")

        assert len(mail.outbox) == 0
        assert "?success=f" in response.get("location")
