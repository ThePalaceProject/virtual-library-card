from unittest.mock import MagicMock

from django import forms
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages

from tests.base import BaseAdminUnitTest
from virtuallibrarycard.admin import CustomUserAdmin
from virtuallibrarycard.forms.forms import CustomAdminUserChangeForm
from virtuallibrarycard.models import (
    CustomUser,
    LibraryAllowedEmailDomains,
    LibraryCard,
)


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
        changes = {
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
            "place": kwargs.get("place_id") or user.place.id,
        }

        # Some changes are either explicit values, or must be omitted
        for key in ("is_staff", "is_superuser"):
            if key in kwargs:
                changes[key] = kwargs[key]

        return changes

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

        msgs = get_messages(response.wsgi_request)
        assert len(msgs) == 2  # created card and save success messages
        for msg in msgs:
            if "Created Library Card" in msg.message:
                break
        else:
            assert False, "'Created Library Card' not found in request messages"

    def test_required_fields_change_form(self):
        response = self.test_client.post(self.get_change_url(self._default_user), {})

        assert response.status_code == 200
        self.assertFormError(
            response, "adminform", "email", ["This field is required."]
        )
        self.assertFormError(
            response, "adminform", "first_name", ["This field is required."]
        )

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
            "street_address_line1",
            ["This field is required."],
        )
        self.assertRaises(
            AttributeError,
            self.assertFormError,
            response,
            "adminform",
            "city",
            ["This field is required."],
        )

        self.assertRaises(
            AttributeError,
            self.assertFormError,
            response,
            "adminform",
            "zip",
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
            [CustomUser.zip.field.validators[0].message],
        )

    def test_read_only_fields(self):
        self.mock_request.user = MagicMock()

        self.mock_request.user.is_superuser = False
        ro_fields = self.admin.get_readonly_fields(self.mock_request)
        assert ["library_cards", "library", "is_superuser"] == ro_fields

    def test_allowed_email_domains(self):
        library = self.create_library()
        LibraryAllowedEmailDomains(library=library, domain="example.org").save()
        user = self.create_user(
            self._default_library,
            email="test@user.com",
            street_address_line1="street",
            city="city",
            zip="99999",
        )

        data = self._get_user_change_data(user, library_id=library.id)
        response = self.test_client.post(self.get_change_url(user), data)

        self.assertFormError(
            response,
            "adminform",
            "email",
            ["Invalid email domain"],
        )

        data = self._get_user_change_data(
            user, library_id=library.id, email="user@example.org"
        )
        response = self.test_client.post(self.get_change_url(user), data)

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.email == "user@example.org"
        assert user.library == library

    def test_age_verification_mandatory(self):
        """over13 field should be a Hidden field now"""
        library = self.create_library(age_verification_mandatory=False)
        user = self.create_user(library)
        form = CustomAdminUserChangeForm(instance=user)
        assert type(form.fields["over13"].widget) == forms.HiddenInput

    def test_list_filter(self):
        self.mock_request.user = MagicMock()
        self.mock_request.user.is_superuser = True
        filters = self.admin.get_list_filter(self.mock_request)
        assert "library" in filters

        self.mock_request.user.is_superuser = False
        filters = self.admin.get_list_filter(self.mock_request)
        assert "library" not in filters

    def test_save_permissions(self):
        """Test whether the save related does the right thing, and changes the permissions"""
        # Start with a simple staff user
        user = self.create_user(self._default_library)
        data = self._get_user_change_data(user, is_staff=True)
        response = self.test_client.post(self.get_change_url(user), data)

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.user_permissions.count() == 8

        # Removing the staff status removes the permissions
        data = self._get_user_change_data(user, is_staff=False)
        response = self.test_client.post(self.get_change_url(user), data)

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.user_permissions.count() == 0

        # superusers get all permissions
        data = self._get_user_change_data(user, is_superuser=True)
        response = self.test_client.post(self.get_change_url(user), data)

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.user_permissions.count() == Permission.objects.count()

        # Reverting back to staff keeps only the staff permissions
        data = self._get_user_change_data(user, is_staff=True)
        response = self.test_client.post(self.get_change_url(user), data)

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.user_permissions.count() == 8
