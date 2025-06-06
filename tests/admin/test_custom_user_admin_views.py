import csv
from unittest.mock import MagicMock

from django import forms
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.test import RequestFactory

from tests.base import BaseAdminUnitTest
from virtuallibrarycard.admin import CustomUserAdmin, export_users_by_consent
from virtuallibrarycard.forms.forms import CustomAdminUserChangeForm
from virtuallibrarycard.models import (
    CustomUser,
    LibraryAllowedEmailDomains,
    LibraryCard,
    UserConsent,
)


class TestCustomUserAdminView(BaseAdminUnitTest):
    MODEL = CustomUser
    MODEL_ADMIN = CustomUserAdmin

    def test_new_user_save(self):
        library = self.create_library()
        response = self.test_client.post(
            self.get_add_url(),
            {
                "email": "test@user.com",
                "password1": "new_pass",
                "password2": "new_pass",
                "first_name": "test",
                "library": library.pk,
            },
        )
        assert response.status_code == 302
        query = CustomUser.objects.filter(email="test@user.com")
        assert query.count() == 1
        assert query.first().library == library

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

    def _get_user_change_data(self, user, consents=None, **kwargs):
        changes = {
            "first_name": kwargs.get("first_name") or user.first_name,
            "last_name": kwargs.get("last_name") or user.last_name or "",
            "library": kwargs.get("library_id") or user.library.id,
            "email": kwargs.get("email") or user.email,
            "over13": "on",
            "is_active": "on",
        }

        # Some changes are either explicit values, or must be omitted
        for key in ("is_staff", "is_superuser"):
            if key in kwargs:
                changes[key] = kwargs[key]

        inline = self.inline_post_data("consents", consents or [])
        changes.update(inline)

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

        self.assertFormError(
            response.context["adminform"],
            "last_name",
            [],
        )

    def test_valid_save_generates_card(self):
        user = self.create_user(
            self._default_library,
            "test@user.com",
            "anypass",
            first_name="first",
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
        )
        data = self._get_user_change_data(user)
        data["email"] = "invalid"

        response = self.test_client.post(self.get_change_url(user), data)

        assert response.status_code == 200
        self.assertFormError(
            response, "adminform", "email", ["Enter a valid email address."]
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
        )

        data = self._get_user_change_data(user, library_id=library.id)
        response = self.test_client.post(self.get_change_url(user), data)

        self.assertFormError(
            response,
            "adminform",
            "email",
            [
                "User must be part of allowed domains: ['example.org']",
                "Invalid email domain",
            ],
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

    def test_export_users_by_consent(self):

        user1 = self.create_user(self._default_library)
        user2 = self.create_user(self._default_library)
        UserConsent.record_consent(
            user1,
            UserConsent.ConsentType.SURVEY,
            UserConsent.ConsentMethod.WEB_CARD_REQUEST,
        )
        UserConsent.record_consent(
            user2,
            UserConsent.ConsentType.SURVEY,
            UserConsent.ConsentMethod.WEB_CARD_REQUEST,
        )

        factory = RequestFactory()

        # Respond with all users with the given consent type
        request = factory.get("/", data=dict(type="SURVEY"))
        request.user = self.super_user
        response = export_users_by_consent(request)

        assert response.status_code == 200
        content = map(lambda x: x.decode(), response.streaming_content)
        reader = csv.DictReader(content)
        assert {r["email"] for r in reader} == {user1.email, user2.email}

        # An unknown type has no users
        request = factory.get("/", data=dict(type="NOTSURVEY"))
        request.user = self.super_user
        response = export_users_by_consent(request)

        assert response.status_code == 200
        content = map(lambda x: x.decode(), response.streaming_content)
        reader = csv.DictReader(content)
        assert {r["email"] for r in reader} == set()

        # Unauthorized
        request = factory.get("/", data=dict(type="SURVEY"))
        request.user = user1
        response = export_users_by_consent(request)
        assert response.status_code == 403
