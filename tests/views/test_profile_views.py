from django.test import RequestFactory

from tests.base import BaseUnitTest
from virtuallibrarycard.models import CustomUser, LibraryCard
from virtuallibrarycard.views.views_profile import ProfileDeleteView


class TestProfileView(BaseUnitTest):
    def test_profile_view(self):
        user = self.create_user(self._default_library)
        l1 = self.create_library_card(user, user.library)
        l2 = self.create_library_card(user, user.library)
        self.client.force_login(user)

        resp = self.client.get("/accounts/profile/")
        assert resp.status_code == 200
        assert resp.context["user"] == user
        assert set(resp.context["library_cards"]) == {l1, l2}
        assert resp.context["nb_library_cards"] == 2

    def test_profile_view_no_login(self):
        resp = self.client.get("/accounts/profile/")
        assert resp.status_code == 302
        assert "/login" in resp.url


class TestProfileDeleteView(BaseUnitTest):
    def test_delete(self):
        user = self.create_user(self._default_library)
        l1 = self.create_library_card(user, user.library)

        request = RequestFactory().get("/account/delete")
        request.user = user
        request.session = {}

        view = ProfileDeleteView()
        view.setup(request)
        response = view.delete(request)

        assert response.status_code == 302
        assert response.url == "delete_profile_success"
        assert CustomUser.objects.filter(id=user.id).count() == 0
        assert LibraryCard.objects.filter(user=user).count() == 0

    def test_delete_no_login(self):
        resp = self.client.delete("/account/delete/somename/")
        assert resp.status_code == 302
        assert "/login" in resp.url

    def test_delete_via_url(self):
        user = self.create_user(self._default_library)
        self.client.force_login(user)

        resp = self.client.delete(f"/account/delete/{user.first_name}/")
        assert resp.status_code == 302
        assert "delete_profile_success" == resp.url

        assert CustomUser.objects.filter(id=user.id).count() == 0


class TestProfileEditView(BaseUnitTest):
    def test_edit_profile_post(self):
        user = self.create_user(self._default_library)
        self.client.force_login(user)

        data = {
            "first_name": "first",
            "last_name": "last",
            "email": "email@t.co",
        }

        response = self.client.post(f"/account/edit/{user.first_name}/", data)

        assert response.status_code == 302
        assert response.url == "/accounts/profile/"

        new_user = CustomUser.objects.get(id=user.id)
        # Test all changed values
        for key, value in data.items():
            assert getattr(new_user, key, None) == value

    def test_edit_profile_required_fields(self):
        user = self.create_user(self._default_library)
        self.client.force_login(user)

        response = self.client.post(f"/account/edit/{user.first_name}/")

        assert response.status_code == 200
        self.assertFormError(
            response, "form", "first_name", ["This field is required."]
        )
        self.assertFormError(response, "form", "email", ["This field is required."])

        # not required fields
        self.assertRaises(
            AssertionError,
            self.assertFormError,
            response,
            "form",
            "last_name",
            ["This field is required."],
        )

    def test_edit_profile_no_login(self):
        response = self.client.get(f"/account/edit/{self._default_user.first_name}/")
        assert response.status_code == 302
        assert "/login" in response.url

        response = self.client.post(f"/account/edit/{self._default_user.first_name}/")
        assert response.status_code == 302
        assert "/login" in response.url


class TestCustomLoginView(BaseUnitTest):
    def test_session_library(self):
        library = self.create_library()

        response = self.client.get(f"/accounts/login/{library.identifier}/")

        assert response.status_code == 200
        assert self.client.session["identifier"] == library.identifier

    def test_login(self):
        password = "somepassword123"
        user = self.create_user(self._default_library, email="example@email.com")
        user.set_password(password)
        user.save()

        response = self.client.post(
            f"/accounts/login/", {"username": user.email, "password": password}
        )
        assert response.status_code == 302
        assert response.url == "/accounts/profile/"

    def test_bad_login(self):
        password = "somepassword123"
        user = self.create_user(self._default_library, email="example@email.com")
        user.set_password(password)
        user.save()

        response = self.client.post(
            f"/accounts/login/", {"username": user.email, "password": "badpassword"}
        )
        assert response.status_code == 200
        self.assertFormError(
            response,
            "form",
            None,
            errors=[
                "Please enter a correct Email address and password. Note that both fields may be case-sensitive."
            ],
        )
