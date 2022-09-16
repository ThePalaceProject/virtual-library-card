from datetime import datetime
from unittest import mock

from django import forms
from django.apps import apps
from django.core import mail
from django.test import Client, RequestFactory

from tests.base import BaseUnitTest
from VirtualLibraryCard.forms.forms_library_card import RequestLibraryCardForm
from VirtualLibraryCard.models import (
    CustomUser,
    LibraryAllowedEmailDomains,
    LibraryCard,
)
from VirtualLibraryCard.views.views_library_card import LibraryCardRequestView


class TestCardSignup(BaseUnitTest):
    @mock.patch("VirtualLibraryCard.views.views_library_card.Geolocalize")
    def test_signup_redirect(self, mock_geolocalize: mock.MagicMock):
        library = self.create_library(us_states=["AL", "NC"])

        # US State 1
        mock_geolocalize.get_user_location.return_value = {
            "results": [
                {
                    "locations": [
                        {
                            "adminArea1": "US",
                            "adminArea3": "AL",
                            "adminArea5": "city",
                            "postalCode": "998867",
                        }
                    ]
                }
            ]
        }

        c = Client()
        resp = c.post(
            f"/account/library_card_signup/{library.identifier}/",
            dict(lat=10, long=10, identifier=library.identifier),
        )
        assert resp.status_code == 302
        assert (
            resp.url
            == f"/account/library_card_request/?identifier={library.identifier}"
        )

        # US State 2
        mock_geolocalize.get_user_location.return_value = {
            "results": [
                {
                    "locations": [
                        {
                            "adminArea1": "US",
                            "adminArea3": "NC",
                            "adminArea5": "city",
                            "postalCode": "998867-55",
                        }
                    ]
                }
            ]
        }

        resp = c.post(
            f"/account/library_card_signup/{library.identifier}/",
            dict(lat=10, long=10, identifier=library.identifier),
        )
        assert resp.status_code == 302
        assert (
            resp.url
            == f"/account/library_card_request/?identifier={library.identifier}"
        )

        assert c.session["zipcode"] == "998867-55"

    @mock.patch("VirtualLibraryCard.views.views_library_card.Geolocalize")
    def test_signup_redirect_negative(self, mock_geolocalize: mock.MagicMock):
        mock_geolocalize.get_user_location.return_value = {
            "results": [
                {
                    "locations": [
                        {
                            "adminArea1": "Not US",
                            "adminArea3": self._default_library.get_first_us_state(),
                            "adminArea5": "city",
                            "postalCode": "998867",
                        }
                    ]
                }
            ]
        }
        c = Client()
        resp = c.post(
            f"/account/library_card_signup/{self._default_library.identifier}/",
            dict(lat=10, long=10, identifier=self._default_library.identifier),
        )
        assert resp.status_code == 200
        assert (
            b"You must be in <strong>USA</strong> to request your library card"
            in resp.content
        )

        mock_geolocalize.get_user_location.return_value = {
            "results": [
                {
                    "locations": [
                        {
                            "adminArea1": "US",
                            "adminArea3": "No state",
                            "adminArea5": "city",
                            "postalCode": "998867",
                        }
                    ]
                }
            ]
        }

        library = self.create_library("MultiState", us_states=["NY", "WA"])
        c = Client()
        resp = c.post(
            f"/account/library_card_signup/{library.identifier}/",
            dict(lat=10, long=10, identifier=library.identifier),
        )
        assert resp.status_code == 200
        assert (
            f"You must be in <strong>{', '.join(library.get_us_states())} </strong> to request"
            in resp.content.decode()
        )

    @mock.patch("VirtualLibraryCard.views.views_library_card.Geolocalize")
    def test_signup_all_states_allowed(self, mock_geolocalize):
        library = self.create_library(allow_all_us_states=True, us_states=[])
        mock_geolocalize.get_user_location.return_value = {
            "results": [
                {
                    "locations": [
                        {
                            "adminArea1": "US",
                            "adminArea3": "Any State",
                            "adminArea5": "city",
                            "postalCode": "998867",
                        }
                    ]
                }
            ]
        }
        c = Client()
        resp = c.post(
            f"/account/library_card_signup/{library.identifier}/",
            dict(lat=10, long=10, identifier=library.identifier),
        )
        assert resp.status_code == 302
        assert (
            resp.url
            == f"/account/library_card_request/?identifier={library.identifier}"
        )


class TestCardRequest(BaseUnitTest):
    def _assert_card_request_success(self, resp, email, library):
        assert resp.status_code == 302
        assert f"/account/library_card_request_success/{email}/" in resp.url
        # New user has been created
        assert CustomUser.objects.filter(email=email).exists()

        # New card was created
        new_user = CustomUser.objects.get(email=email)
        assert LibraryCard.objects.filter(user=new_user, library=library).exists()

    def _get_card_request_data(self, library, email, **data):
        post = dict(
            library=library.id,
            country_code="US",
            first_name="New",
            last_name="User",
            email=email,
            street_address_line1="Some street",
            street_address_line2="",
            city="city",
            us_state=library.get_first_us_state(),
            zip="99887",
            over13="on",
            password1="xx123456789",
            password2="xx123456789",
            **{"g-recaptcha-response": "xxxcaptcha"},
        )
        post.update(data)
        return post

    @mock.patch("VirtualLibraryCard.business_rules.library.AddressChecker")
    def test_card_request(self, mock_checker, with_captcha=True):
        c = Client()

        # Prime the session
        self.do_library_card_signup_flow(c)

        # Mock the address check
        mock_checker.is_valid_zipcode.return_value = True

        identifier = self._default_library.identifier
        captcha = {"g-recaptcha-response": "xxxcaptcha"} if with_captcha else {}
        resp = c.post(
            f"/account/library_card_request/?identifier={identifier}",
            self._get_card_request_data(
                self._default_library, "test@example.com", **captcha
            ),
        )

        self._assert_card_request_success(
            resp, "test@example.com", self._default_library
        )

        # Verification and welcome email sent
        assert len(mail.outbox) == 2
        assert mail.outbox[0].subject == f"{self._default_library.name} | Welcome"
        assert mail.outbox[1].subject == "Verify your email address New"
        assert (
            "You must verify your email address before using this account"
            in mail.outbox[0].body
        )

    @mock.patch("VirtualLibraryCard.business_rules.library.AddressChecker")
    def test_card_request_bad_data(self, mock_checker):
        c = Client()

        # Prime the session
        self.do_library_card_signup_flow(c)

        # Mock the address check
        mock_checker.is_valid_zipcode.return_value = True

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

        expected_errors_fields = [
            "first_name",
            "email",
            "street_address_line1",
            "zip",
            "captcha",
        ]
        for field in expected_errors_fields:
            self.assertFormError(resp, "form", field, ["This field is required."])

    @mock.patch("VirtualLibraryCard.business_rules.library.AddressChecker")
    def test_card_request_no_patron_address(self, mock_checker):
        c = Client()

        library = self.create_library(patron_address_mandatory=False)
        # Prime the session
        self.do_library_card_signup_flow(c, library=library)

        # Mock the address checker as Nonetype, but it shouldn't matter
        mock_checker.is_valid_zipcode = None

        identifier = library.identifier
        resp = c.post(
            f"/account/library_card_request/?identifier={identifier}",
            self._get_card_request_data(
                library,
                "test@example.com",
                country_code="CA",
                street_address_line1="",
                zip="",
                city="",
            ),
        )
        self._assert_card_request_success(resp, "test@example.com", library)

        ## Form specifics
        user = self.create_user(library)
        form = RequestLibraryCardForm(instance=user)
        for name in ("city", "zip", "street_address_line1", "street_address_line2"):
            assert form.fields[name].required == False
            assert type(form.fields[name].widget) == forms.HiddenInput

    @mock.patch("VirtualLibraryCard.business_rules.library.AddressChecker")
    def test_card_request_email_no_duplicates(self, mock_checker):
        user = self.create_user(self._default_library, "TEST@t.co")
        c = Client()

        library = self.create_library(patron_address_mandatory=False)
        # Prime the session
        self.do_library_card_signup_flow(c, library=library)

        # Mock the address checker as Nonetype, but it shouldn't matter
        mock_checker.is_valid_zipcode = None

        error_args = ("form", "email", ["Email address already in use"])

        post_dict = self._get_card_request_data(library, user.email)
        identifier = library.identifier

        for test_email in [
            user.email,
            user.email.upper(),
            user.email.lower(),
            "TEst@T.co",
        ]:
            post_dict["email"] = test_email
            resp = c.post(
                f"/account/library_card_request/?identifier={identifier}",
                post_dict,
            )
            self.assertFormError(resp, *error_args)

    def test_card_request_no_captcha_installed(self):
        # Remove captcha from the installed apps
        installed_apps = [ac.name for ac in apps.get_app_configs()]
        installed_apps.remove("captcha")
        apps.set_installed_apps(installed_apps)

        new_apps = [ac.name for ac in apps.get_app_configs()]
        assert "captcha" not in new_apps
        self.test_card_request(with_captcha=False)
        apps.unset_installed_apps()

    @mock.patch("VirtualLibraryCard.business_rules.library.AddressChecker")
    def test_card_invalid_email_domain(self, mock_checker):
        library = self.create_library()
        LibraryAllowedEmailDomains(library=library, domain="example.org").save()

        client = Client()
        self.do_library_card_signup_flow(client, library)

        post_dict = dict(
            library=library.id,
            country_code="US",
            first_name="New",
            last_name="User",
            email="user@notexample.com",
            street_address_line1="Some street",
            street_address_line2="",
            city="city",
            us_state=library.get_first_us_state(),
            zip="99887",
            over13="on",
            password1="xx123456789",
            password2="xx123456789",
            **{"g-recaptcha-response": "xxxcaptcha"},
        )

        resp = client.post(
            f"/account/library_card_request/?identifier={library.identifier}",
            post_dict,
        )

        self.assertFormError(
            resp,
            "form",
            "email",
            errors=["User must be part of allowed domains: ['example.org']"],
        )

    @mock.patch("VirtualLibraryCard.business_rules.library.AddressChecker")
    def test_age_verification(self, mock_checker):
        """over13 form field should be hidden and default to false"""
        library = self.create_library(age_verification_mandatory=False)
        client = Client()
        self.do_library_card_signup_flow(client, library)
        # We want to test the form_kwargs method specifically
        request = RequestFactory().get(
            f"/account/library_card_request/?identifier={library.identifier}"
        )
        request.session = client.session
        view = LibraryCardRequestView(request=request)
        view.get_form_kwargs()
        assert view.model.over13 == False
        # And the corresponding form created with the same model
        form = RequestLibraryCardForm(instance=view.model)
        assert type(form.fields["over13"].widget) == forms.HiddenInput
        assert form.instance.over13 == False

        ## Do an actual request
        resp = client.post(
            f"/account/library_card_request/?identifier={library.identifier}",
            self._get_card_request_data(library, "user@example.org", over13="False"),
        )

        self._assert_card_request_success(resp, "user@example.org", library)
        user = CustomUser.objects.filter(email="user@example.org").first()
        assert user.over13 == False


class TestLibraryCardDelete(BaseUnitTest):
    def test_delete_library_card(self):

        user = self.create_user(self._default_library, username="xxxx")
        card = self.create_library_card(user, self._default_library)

        self.client.force_login(user)
        response = self.client.post(
            f"/account/library_cards/cancel/{card.number}",
            {"number": card.number},
        )

        assert response.status_code == 302
        assert response.url == "/account/profile/True/True/"
        new_card = LibraryCard.objects.get(number=card.number)
        assert new_card.canceled_date.date() == datetime.today().date()
        assert new_card.canceled_by_user == user.username

    def test_delete_no_login(self):
        user = self.create_user(self._default_library, username="xxxx")
        card = self.create_library_card(user, self._default_library)

        response = self.client.post(
            f"/account/library_cards/cancel/{card.number}",
            {"number": card.number},
        )

        assert response.status_code == 302
        assert "/login" in response.url

    def test_required_fields(self):
        user = self.create_user(self._default_library, username="xxxx")
        card = self.create_library_card(user, self._default_library)

        self.client.force_login(user)
        response = self.client.post(f"/account/library_cards/cancel/{card.number}")

        self.assertFormError(response, "form", "number", ["This field is required."])

    def test_update_user_library(self):
        """I have no idea what this functions purpose is,
        but it changes the users library based on the first card found
        after a delete.
        THIS DOESN'T WORK THOUGH
        The self.instance gets reset with stale values after
        super().commit is called
        To fix this self.instance should to refreshed before calling
        super().commit"""
        user = self.create_user(self._default_library, username="xxxx")
        card = self.create_library_card(user, self._default_library)

        library = self.create_library()
        card1 = self.create_library_card(user, library)

        # assert the card and user libraries are not the same
        assert card1.library != user.library

        self.client.force_login(user)
        response = self.client.post(
            f"/account/library_cards/cancel/{card.number}",
            {"number": card.number},
        )

        assert response.status_code == 302
        new_user = CustomUser.objects.get(id=user.id)
        # This should have been `card1.library` not `self._default_library`
        assert self._default_library == new_user.library