from unittest.mock import MagicMock

from tests.base import BaseAdminUnitTest
from VirtualLibraryCard.admin import CustomUserAdmin
from VirtualLibraryCard.models import CustomUser, LibraryCard


class TestCustomUserAdminView(BaseAdminUnitTest):
    MODEL = CustomUser
    MODEL_ADMIN = CustomUserAdmin

    def test_new_user_save(self):
        response = self.test_client.post(
            self.get_add_url(),
            {
                "email": "test@user.com",
                "password1": "new_pass",
                "password2": "new_pass",
                "first_name": "test",
            },
        )
        assert response.status_code == 302
        assert CustomUser.objects.filter(email="test@user.com").count() == 1

    def test_new_user_save_errors(self):
        response = self.test_client.post(
            self.get_add_url(),
            {
                "email": "test@user.com",
                "password1": "new_pass",
                "password2": "new_pass__",
                "first_name": "test",
            },
        )

        assert response.status_code == 200
        self.assertFormError(
            response,
            "adminform",
            "password2",
            ["The two password fields didn’t match."],
        )

        # No required fields
        response = self.test_client.post(
            self.get_add_url(),
            {"last_name": "not required"},
        )

        assert response.status_code == 200
        self.assertFormError(
            response, "adminform", "email", ["This field is required."]
        )
        self.assertFormError(
            response, "adminform", "password1", ["This field is required."]
        )
        self.assertFormError(
            response, "adminform", "password2", ["This field is required."]
        )
        self.assertFormError(
            response, "adminform", "first_name", ["This field is required."]
        )

        # No required fields
        response = self.test_client.post(
            self.get_add_url(),
            {
                "email": "testuser",
                "password1": "new_pass",
                "password2": "new_pass",
                "first_name": "test",
            },
        )

        assert response.status_code == 200
        self.assertFormError(
            response, "adminform", "email", ["Enter a valid email address."]
        )

    def _get_user_change_data(self, user, **kwargs):
        return {
            "first_name": kwargs.get("first_name") or user.first_name,
            "last_name": kwargs.get("last_name") or user.last_name or "",
            "library": kwargs.get("library_id") or user.library.id,
            "email": kwargs.get("email") or user.email,
            "street_address_line1": kwargs.get("street_address_line1")
            or user.street_address_line1
            or "",
            "street_address_line2": kwargs.get("street_address_line2")
            or user.street_address_line2
            or "",
            "city": kwargs.get("city") or user.city or "",
            "zip": kwargs.get("zip") or user.zip or "",
            "over13": "on",
            "is_active": "on",
        }

    def test_valid_change_form(self):
        user = self.create_user(
            self._default_library, "test@user.com", "anypass", first_name="first"
        )
        changes = dict(
            first_name="new name",
            last_name="new last name",
            email="new@email.com",
            street_address_line1="street_address",
            street_address_line2="street_address2",
            city="city",
            zip="99999",
        )
        data = self._get_user_change_data(user, **changes)

        response = self.test_client.post(self.get_change_url(user), data)
        assert response.status_code == 302

        assert CustomUser.objects.filter(email="test@user.com").count() == 0
        changed_user: CustomUser = CustomUser.objects.get(email="new@email.com")
        assert changed_user.first_name == "new name"
        assert changed_user.last_name == "new last name"
        assert changed_user.street_address_line1 == "street_address"
        assert changed_user.street_address_line2 == "street_address2"
        assert changed_user.city == "city"
        assert changed_user.zip == "99999"

    def test_required_fields_change_form(self):
        response = self.test_client.post(self.get_change_url(self._default_user), {})

        assert response.status_code == 200
        self.assertFormError(
            response, "adminform", "email", ["This field is required."]
        )
        self.assertFormError(
            response, "adminform", "first_name", ["This field is required."]
        )
        self.assertFormError(
            response, "adminform", "street_address_line1", ["This field is required."]
        )
        self.assertFormError(response, "adminform", "city", ["This field is required."])
        self.assertFormError(response, "adminform", "zip", ["This field is required."])

        # not required fields
        self.assertRaises(
            AttributeError,
            self.assertFormError,
            response,
            "adminform",
            "last_name",
            ["This field is required."],
        )

        self.assertRaises(
            AttributeError,
            self.assertFormError,
            response,
            "adminform",
            "street_address_line2",
            ["This field is required."],
        )

    def test_valid_save_generates_card(self):
        user = self.create_user(
            self._default_library,
            "test@user.com",
            "anypass",
            first_name="first",
            street_address_line1="street",
            city="city",
            zip="99999",
        )

        # no card up front
        assert LibraryCard.objects.filter(user=user).count() == 0

        data = self._get_user_change_data(user)
        response = self.test_client.post(self.get_change_url(user), data)

        assert response.status_code == 302
        card = LibraryCard.objects.get(user=user)
        assert card.library == self._default_library

    def test_field_formats_change_form(self):
        user = self.create_user(
            self._default_library,
            "test1@user.com",
            "anypass",
            first_name="first",
            street_address_line1="street",
            city="city",
            zip="99999",
        )
        data = self._get_user_change_data(user)
        data["email"] = "invalid"
        data["zip"] = "invalid"

        response = self.test_client.post(self.get_change_url(user), data)

        assert response.status_code == 200
        self.assertFormError(
            response, "adminform", "email", ["Enter a valid email address."]
        )
        self.assertFormError(
            response,
            "adminform",
            "zip",
            ["Enter a zip code in the format XXXXX or XXXXX-XXXX."],
        )

    def test_read_only_fields(self):
        self.mock_request.user = MagicMock()

        self.mock_request.user.is_superuser = False
        ro_fields = self.admin.get_readonly_fields(self.mock_request)
        assert ["library_cards", "library"] == ro_fields

        self.mock_request.user.is_superuser = False
        ro_fields = self.admin.get_readonly_fields(
            self.mock_request, obj=self._default_user
        )
        assert ["library_cards", "library", "us_state"] == ro_fields
