from io import FileIO
from typing import List
from unittest.mock import MagicMock

from django.test import RequestFactory

from tests.base import BaseAdminUnitTest
from VirtualLibraryCard.admin import (
    LibraryAdmin,
    LibraryAllowedDomainsInline,
    LibraryStatesInline,
)
from VirtualLibraryCard.models import Library, LibraryStates


class TestLibraryAdminViews(BaseAdminUnitTest):
    MODEL = Library
    MODEL_ADMIN = LibraryAdmin

    def _get_library_change_data(self, library, **changes):
        required_fields = {
            "identifier": "",
            "name": "",
            "logo": FileIO("tests/files/logo.png"),
            "privacy_url": "",
            "terms_conditions_url": "",
            "phone": "",
            "email": "",
            "prefix": "",
            "bulk_upload_prefix": "",
            "sequence_start_number": 0,
            "sequence_down": False,
            "patron_address_mandatory": True,
            "age_verification_mandatory": True,
            "pin_text": "pin",
            "barcode_text": "barcode",
            "allow_all_us_states": False,
            "allow_bulk_card_uploads": False,
        }

        data = {}
        for key, value in required_fields.items():
            data[key] = changes.get(key, getattr(library, key, value))

        self._add_library_states_data(
            data, library=library, us_states=changes.get("us_states")
        )
        return data

    def _add_library_states_data(
        self, data: dict, us_states: List[str] = None, library=None
    ):
        """Helper function for change form data, for the inline library form"""
        us_states = us_states or []
        prev_states = list(LibraryStates.objects.filter(library=library).all())
        total_prev_states = len(prev_states)
        total_forms = len(us_states + prev_states)

        data.update(
            {
                "library_email_domains-TOTAL_FORMS": 0,
                "library_email_domains-INITIAL_FORMS": 0,
                "library_email_domains-MIN_NUM_FORMS": 0,
                "library_email_domains-MAX_NUM_FORMS": 1000,
                "library_email_domains-__prefix__-library": library.id
                if library
                else "",
            }
        )

        data.update(
            {
                "library_states-TOTAL_FORMS": total_forms,
                "library_states-INITIAL_FORMS": total_prev_states,
                "library_states-MIN_NUM_FORMS": 0,
                "library_states-MAX_NUM_FORMS": 1000,
            }
        )

        for ix, state in enumerate(prev_states):
            data.update(
                {
                    f"library_states-{ix}-id": state.id,
                    f"library_states-{ix}-library": library.id,
                    f"library_states-{ix}-us_state": state.us_state,
                }
            )

        for ix, state in enumerate(us_states):
            idx = ix + total_prev_states
            data.update(
                {
                    f"library_states-{idx}-id": "",
                    f"library_states-{idx}-library": library.id,
                    f"library_states-{idx}-us_state": state,
                }
            )

        if library:
            data.update(
                {
                    f"library_states-__prefix__-id": "",
                    f"library_states-__prefix__-library": library.id,
                    f"library_states-__prefix__-us_state": "",
                }
            )

        return data

    def test_create_library(self):

        data = dict(
            identifier="new",
            name="new",
            logo=FileIO("tests/files/logo.png"),
            privacy_url="privacyurl",
            terms_conditions_url="termsurl",
            prefix="new",
            bulk_upload_prefix="bulk",
            sequence_start_number=0,
            sequence_down=False,
            patron_address_mandatory=True,
            age_verification_mandatory=True,
            pin_text="pin",
            barcode_text="barcode",
            allow_all_us_states=False,
            allow_bulk_card_uploads=False,
        )
        self._add_library_states_data(data)

        response = self.test_client.post(self.get_add_url(), data)
        assert response.status_code == 302
        assert Library.objects.filter(identifier="new").count() == 1

    def test_create_library_required_fields(self):
        data = dict(
            identifier="",
            name="",
            # logo="", # no logo
            privacy_url="",
            terms_conditions_url="",
            prefix="",
            # sequence_start_number=0,
            # sequence_down=False,
        )
        self._add_library_states_data(data)
        response = self.test_client.post(self.get_add_url(), data)

        self.assertFormError(
            response, "adminform", "identifier", ["This field is required."]
        )
        self.assertFormError(response, "adminform", "name", ["This field is required."])
        self.assertFormError(
            response, "adminform", "privacy_url", ["This field is required."]
        )
        self.assertFormError(
            response, "adminform", "terms_conditions_url", ["This field is required."]
        )
        self.assertFormError(
            response, "adminform", "prefix", ["This field is required."]
        )
        self.assertFormError(
            response, "adminform", "sequence_start_number", ["This field is required."]
        )
        self.assertFormError(
            response, "adminform", "sequence_down", ["This field is required."]
        )
        self.assertFormError(response, "adminform", "logo", ["This field is required."])
        self.assertFormError(
            response, "adminform", "barcode_text", ["This field is required."]
        )
        self.assertFormError(
            response, "adminform", "pin_text", ["This field is required."]
        )

    def test_change_library_valid(self):
        changes = {
            "identifier": "newid",
            "prefix": "newid",
            "name": "newid",
            "sequence_start_number": 99,
            "logo": FileIO("tests/files/logo.png"),
        }
        data = self._get_library_change_data(self._default_library, **changes)
        response = self.test_client.post(
            self.get_change_url(self._default_library), data
        )
        assert response.status_code == 302

        library: Library = Library.objects.get(identifier="newid")
        assert library.prefix == "newid"
        assert library.name == "newid"
        assert library.sequence_start_number == 99

    def test_library_add_states(self):
        library = self.create_library(name="test", us_states=["FL"])
        data = self._get_library_change_data(library, us_states=["NY"], prefix="pref")
        del data["logo"]  # Don't need a logo if it exists

        response = self.test_client.post(self.get_change_url(library), data)

        assert response.status_code == 302
        saved = Library.objects.get(id=library.id)
        assert saved.get_us_states() == ["FL", "NY"]

    def test_read_only_fields(self):
        self.mock_request.user = MagicMock()

        self.mock_request.user.is_superuser = True
        assert [] == self.admin.get_readonly_fields(self.mock_request)

        self.mock_request.user.is_superuser = False
        assert ["identifier"] == self.admin.get_readonly_fields(self.mock_request)

    def test_add_allowed_email_domain(self):
        library = self.create_library()
        changes = self._get_library_change_data(library)
        changes.update(
            {
                "library_email_domains-TOTAL_FORMS": 1,
                "library_email_domains-INITIAL_FORMS": 0,
                "library_email_domains-MIN_NUM_FORMS": 0,
                "library_email_domains-MAX_NUM_FORMS": 100,
                "library_email_domains-0-id": "",
                "library_email_domains-0-library": library.id,
                "library_email_domains-0-domain": "example.org",
            }
        )
        del changes["logo"]

        response = self.test_client.post(self.get_change_url(library), changes)
        assert response.status_code == 302

        library.refresh_from_db()
        assert len(library.library_email_domains.all()) == 1
        assert library.library_email_domains.all()[0].domain == "example.org"

    def test_get_inlines(self):
        f = RequestFactory()
        get = f.get("")
        post_has_states = f.post("", {"library_states-TOTAL_FORMS": "0"})
        library = self.create_library(allow_all_us_states=False)

        # View a library that doesn't allow all states
        assert self.admin.get_inlines(get, obj=library) == [
            LibraryStatesInline,
            LibraryAllowedDomainsInline,
        ]
        # Change a library to not allow all states
        assert self.admin.get_inlines(post_has_states, obj=library) == [
            LibraryStatesInline,
            LibraryAllowedDomainsInline,
        ]

        # Change a library to allow all states
        post_without_states = f.post("", {})
        assert self.admin.get_inlines(post_without_states, obj=library) == [
            LibraryAllowedDomainsInline
        ]
        # View a library with all states
        library.allow_all_us_states = True
        assert self.admin.get_inlines(get, obj=library) == [LibraryAllowedDomainsInline]

        # New object view/creation
        assert self.admin.get_inlines(get, obj=None) == [
            LibraryStatesInline,
            LibraryAllowedDomainsInline,
        ]
        assert self.admin.get_inlines(post_has_states, obj=None) == [
            LibraryStatesInline,
            LibraryAllowedDomainsInline,
        ]
        assert self.admin.get_inlines(post_without_states, obj=None) == [
            LibraryAllowedDomainsInline,
        ]
