from django.core import mail

from tests.base import BaseUnitTest


class TestPasswordResetView(BaseUnitTest):
    def test_reset_post(self):
        response = self.client.post(
            "/account/reset-password/", {"email": self._default_user.email}
        )

        assert response.context.get("token") is not None
        assert len(mail.outbox) == 1

        reset_mail = mail.outbox[0]
        assert reset_mail.to == [self._default_user.email]
        assert reset_mail.subject == "Virtual Library Card | Password Reset"

    def test_bad_email(self):
        response = self.client.post(
            "/account/reset-password/", {"email": "nosuchemail@email.com"}
        )
        self.assertFormError(
            response,
            "form",
            "email",
            [
                "There is no user registered with the specified email address nosuchemail@email.com"
            ],
        )

        response = self.client.post("/account/reset-password/")
        self.assertFormError(
            response,
            "form",
            "email",
            ["This field is required."],
        )


class TestPasswordChangeView(BaseUnitTest):
    def test_password_change_form(self):
        old_password = "apassword"
        new_password = "jalasd8838383"

        user = self._default_user
        user.set_password(old_password)
        user.save()
        self.client.force_login(user)

        response = self.client.post(
            f"/account/change-password/{self._default_user.first_name}/",
            {
                "old_password": old_password,
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )

        assert response.status_code == 302
        assert response.url == "password_change_done"

        assert (
            self.client.login(username=self._default_user.email, password=old_password)
            == False
        )
        assert (
            self.client.login(username=self._default_user.email, password=new_password)
            == True
        )

    def test_required_fields(self):
        self.client.force_login(self._default_user)
        response = self.client.post(
            f"/account/change-password/{self._default_user.first_name}/"
        )

        assert response.status_code == 200
        self.assertFormError(
            response, "form", "old_password", ["This field is required."]
        )
        self.assertFormError(
            response, "form", "new_password1", ["This field is required."]
        )
        self.assertFormError(
            response, "form", "new_password2", ["This field is required."]
        )

    def test_login_required(self):
        response = self.client.post(
            f"/account/change-password/{self._default_user.first_name}/"
        )

        assert response.status_code == 302
        assert "/login" in response.url
