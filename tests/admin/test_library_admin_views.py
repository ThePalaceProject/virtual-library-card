from __future__ import annotations

from io import FileIO
from unittest.mock import MagicMock

from tests.base import BaseAdminUnitTest
from virtuallibrarycard.admin import LibraryAdmin
from virtuallibrarycard.models import Library, Place


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
            "allow_bulk_card_uploads": False,
            "has_survey_consent": False,
        }

        data = {}
        for key, value in required_fields.items():
            data[key] = changes.get(key, getattr(library, key, value))

        self._add_library_states_data(
            data, library=library, places=changes.get("places")
        )
        return data

    def _add_library_states_data(
        self, data: dict, places: list[str] = None, library=None
    ):
        """Helper function for change form data, for the inline library form"""
        places = places or []
        place_ids = [p.id for p in Place.objects.filter(abbreviation__in=places).all()]
        data["places_filter"] = place_ids

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
            allow_bulk_card_uploads=False,
            has_survey_consent=False,
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
            allow_bulk_card_uploads=False,
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

    def test_create_library_with_places(self):
        library = self.create_library(places=[])
        data = self._get_library_change_data(library)
        # Change the data to create a new library
        data.update(
            {
                "identifier": "newWithPlace",
                "logo": FileIO("tests/files/logo.png"),
            }
        )
        data = self._add_library_states_data(data, ["NY", "AK"])
        response = self.test_client.post(self.get_add_url(), data)

        assert response.status_code == 302, response.context["adminform"].errors
        assert sorted(
            Library.objects.get(identifier=data["identifier"]).get_places()
        ) == ["AK", "NY"]

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
        library = self.create_library(name="test", places=["FL"])
        data = self._get_library_change_data(library, places=["NY"], prefix="pref")
        del data["logo"]  # Don't need a logo if it exists

        response = self.test_client.post(self.get_change_url(library), data)

        assert response.status_code == 302
        saved = Library.objects.get(id=library.id)
        assert saved.get_places() == ["NY"]

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

    def test_optional_bulk_upload_prefix(self):
        """If the allow_bulk_card_uploads attribute is true then the bulk uploads prefix is mandatory,
        else it is optional"""
        library = self.create_library()
        changes = self._get_library_change_data(library, allow_bulk_card_uploads=True)
        del changes["logo"]
        del changes["bulk_upload_prefix"]
        response = self.test_client.post(self.get_change_url(library), changes)

        assert response.status_code == 200
        self.assertFormError(
            response,
            "adminform",
            "bulk_upload_prefix",
            "When bulk card uploads are allowed, this field must be given a value.",
        )

        # When allow_bulk_card_uploads is False, the field is optional
        changes["allow_bulk_card_uploads"] = False
        response = self.test_client.post(self.get_change_url(library), changes)
        assert response.status_code == 302

        # When allow_bulk_card_uploads is True, and the field is provided we're A-OK
        changes["bulk_upload_prefix"] = "bulkupload"
        changes["allow_bulk_card_uploads"] = True
        response = self.test_client.post(self.get_change_url(library), changes)
        assert response.status_code == 302
