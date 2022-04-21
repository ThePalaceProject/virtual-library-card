from io import StringIO
from unittest import mock

import html5lib
from base import BaseUnitTest
from django.test import Client

from VirtualLibraryCard.models import CustomUser, LibraryCard


class TestCardRequest(BaseUnitTest):
    @mock.patch("VirtualLibraryCard.forms.forms_library_card.AddressChecker")
    def test_card_request(self, mock_checker):
        c = Client()

        # Prime the session
        self.do_library_card_signup_flow(c)

        # Mock the address check
        mock_checker.is_valid_postal_address.return_value = True

        identifier = self._default_library.identifier
        resp = c.post(
            f"/account/library_card_request/?identifier={identifier}",
            dict(
                library=self._default_library.id,
                country_code="US",
                first_name="New",
                last_name="User",
                email="test@example.com",
                street_address_line1="Some street",
                street_address_line2="",
                city="city",
                us_state=self._default_library.get_first_us_state(),
                zip="99887",
                over13="on",
                password1="xx123456789",
                password2="xx123456789",
            ),
        )

        assert resp.status_code == 302
        assert "/account/library_card_request_success/test@example.com/" in resp.url
        # New user has been created
        assert CustomUser.objects.filter(email="test@example.com").exists()

        # New card was created
        new_user = CustomUser.objects.get(email="test@example.com")
        assert LibraryCard.objects.filter(
            user=new_user, library=self._default_library
        ).exists()

    @mock.patch("VirtualLibraryCard.forms.forms_library_card.AddressChecker")
    def test_card_request_bad_data(self, mock_checker):
        c = Client()

        # Prime the session
        self.do_library_card_signup_flow(c)

        # Mock the address check
        mock_checker.is_valid_postal_address.return_value = True

        identifier = self._default_library.identifier
        resp = c.post(
            f"/account/library_card_request/?identifier={identifier}",
            dict(
                library=self._default_library.id,
                country_code="CA",  # Not US
                # first_name="New", # No first name
                last_name="User",
                # email="test@example.com", # No Email
                # street_address_line1="Some street", # No street address
                street_address_line2="",
                city="city",
                us_state=self._default_library.get_first_us_state(),
                # zip="99887",
                over13="on",
                password1="xx123456789",
                password2="xx123456789",
            ),
        )

        content: str = resp.content.decode()

        etree = html5lib.HTMLParser().parse(StringIO(content))
        walker = html5lib.getTreeWalker("etree")(etree)

        expected_errors_fields = [
            "First name",
            "Email address",
            "Street address line 1",
            "Zip code",
        ]
        last_expected_ix = 0
        last_expected_field = ""
        found_errors = []
        for ix, tag in enumerate(walker):
            # Find the write fields
            if tag["type"] == "Characters" and tag["data"] in expected_errors_fields:
                last_expected_ix = ix
                last_expected_field = tag["data"]
            elif (
                tag["type"] == "Characters" and tag["data"] == "This field is required."
            ):
                # We are within expeced bounds
                if (last_expected_ix + 10) > ix:
                    found_errors.append(last_expected_field)

        assert expected_errors_fields == found_errors
