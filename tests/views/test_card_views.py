from datetime import datetime
from unittest import mock

import pytest
from django import forms
from django.apps import apps
from django.core import mail
from django.test import Client, RequestFactory

from tests.base import BaseUnitTest
from virtuallibrarycard.forms.forms_library_card import RequestLibraryCardForm
from virtuallibrarycard.models import (
    CustomUser,
    LibraryAllowedEmailDomains,
    LibraryCard,
    LibraryPlace,
    Place,
    UserConsent,
)
from virtuallibrarycard.views.views_library_card import (
    CardSignupView,
    InvalidUserLocation,
    LibraryCardRequestView,
)


class TestCardSignup(BaseUnitTest):
    def _get_mock_geolocalize_value(
        self, country=None, state=None, county=None, city=None
    ):
        return {
            "results": [
                {
                    "locations": [
                        {
                            "adminArea1": country or "US",
                            "adminArea3": state or "AL",
                            "adminArea4": county or "ALC",
                            "adminArea5": city or "city",
                            "postalCode": "998867",
                        }
                    ]
                }
            ]
        }

    @mock.patch("virtuallibrarycard.views.views_library_card.Geolocalize")
    @mock.patch("virtuallibrarycard.views.views_library_card.UserSessionManager")
    def test_validate_location(
        self, mock_manager: mock.MagicMock, mock_geolocalize: mock.MagicMock
    ):
        library = self.create_library(places=["AL", "NC"])
        rf = RequestFactory()
        view = CardSignupView()

        # Valid request sets the session data and success url
        mock_geolocalize.get_user_location.return_value = (
            self._get_mock_geolocalize_value(state="AL")
        )
        view.request = rf.get("/")
        assert view._validate_location(library, 99, 99) == None
        assert (
            view.success_url
            == f"/account/library_card_request/?identifier={library.identifier}"
        )
        assert mock_manager.set_session_library.call_count == 1
        assert mock_manager.set_session_user_location.call_count == 1
        assert mock_manager.set_session_user_location.call_args == mock.call(
            view.request, "US", "AL", "city", "998867"
        )

        # An invalid request raise an error
        mock_geolocalize.get_user_location.return_value = (
            self._get_mock_geolocalize_value(state="NY")
        )
        with pytest.raises(InvalidUserLocation):
            view._validate_location(library, 99, 99)

    @mock.patch("virtuallibrarycard.views.views_library_card.Geolocalize")
    def test_signup_redirect(self, mock_geolocalize: mock.MagicMock):
        library = self.create_library(places=["AL", "NC"])

        # US State 1
        mock_geolocalize.get_user_location.return_value = (
            self._get_mock_geolocalize_value(state="AL")
        )

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
        mock_geolocalize.get_user_location.return_value = (
            self._get_mock_geolocalize_value(state="NC")
        )

        resp = c.post(
            f"/account/library_card_signup/{library.identifier}/",
            dict(lat=10, long=10, identifier=library.identifier),
        )
        assert resp.status_code == 302
        assert (
            resp.url
            == f"/account/library_card_request/?identifier={library.identifier}"
        )

        assert c.session["zipcode"] == "998867"

    @mock.patch("virtuallibrarycard.views.views_library_card.Geolocalize")
    def test_signup_redirect_admin_levels(self, mock_geolocalize: mock.MagicMock):
        """Test all allowed adminarea levels against the address validation"""
        country = Place(
            name="Country",
            abbreviation="cntry",
            type=Place.Types.COUNTRY,
            parent=None,
            external_id="1",
        )
        state = Place(
            name="State",
            abbreviation="stt",
            type=Place.Types.STATE,
            parent=country,
            external_id="2",
        )
        province = Place(
            name="Province",
            abbreviation="prvnc",
            type=Place.Types.PROVINCE,
            parent=country,
            external_id="3",
        )
        county = Place(
            name="County",
            abbreviation="cnty",
            type=Place.Types.COUNTY,
            parent=state,
            external_id="4",
        )
        city = Place(
            name="City",
            abbreviation="cty",
            type=Place.Types.CITY,
            parent=county,
            external_id="5",
        )

        country.save(), state.save(), province.save(), county.save(), city.save()

        library = self.create_library(name="Test", identifier="Test", places=["NY"])

        locations = [
            ("country", dict(country=country)),
            ("state", dict(state=province, country=country)),
            ("state", dict(state=state, country=country)),
            ("county", dict(county=county, state=state, country=country)),
            ("city", dict(city=city, county=county, state=state, country=country)),
        ]

        c = Client()

        for type, places in locations:
            # Run through all location types and ensure the form post is a success
            check_strs = {name: p.check_str for name, p in places.items()}
            mock_geolocalize.get_user_location.return_value = (
                self._get_mock_geolocalize_value(**check_strs)
            )
            place = places[type]
            # Associate the library to this place
            lp = LibraryPlace(library=library, place=place)
            lp.save()

            resp = c.post(
                f"/account/library_card_signup/{library.identifier}/",
                dict(lat=10, long=10, identifier=library.identifier),
            )
            assert resp.status_code == 302, resp.context["form"].errors
            assert (
                resp.url
                == f"/account/library_card_request/?identifier={library.identifier}"
            )

            # Remove the association, so the next loop is not tainted
            lp.delete()

    @mock.patch("virtuallibrarycard.views.views_library_card.Geolocalize")
    def test_signup_redirect_negative(self, mock_geolocalize: mock.MagicMock):

        mock_geolocalize.get_user_location.return_value = (
            self._get_mock_geolocalize_value(state="No State")
        )

        library = self.create_library("MultiState", places=["NY", "WA"])
        c = Client()
        resp = c.post(
            f"/account/library_card_signup/{library.identifier}/",
            dict(lat=10, long=10, identifier=library.identifier),
        )
        assert resp.status_code == 200
        assert (
            f"You must be in <strong>{', '.join(library.get_places())} </strong> to request"
            in resp.content.decode()
        )

    @mock.patch("virtuallibrarycard.views.views_library_card.Geolocalize")
    def test_signup_all_states_allowed(self, mock_geolocalize):
        library = self.create_library(places=["US"])
        mock_geolocalize.get_user_location.return_value = (
            self._get_mock_geolocalize_value(country="US")
        )
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
        assert resp.status_code == 302, resp.context["form"].errors
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
            place=library.places[0].id,
            zip="99887",
            over13="on",
            password1="xx123456789",
            password2="xx123456789",
            consent="on",
            **{"g-recaptcha-response": "xxxcaptcha"},
        )
        post.update(data)
        return post

    def test_card_request(self, with_captcha=True):
        c = Client()

        # Prime the session
        self.do_library_card_signup_flow(c)

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
        user = CustomUser.objects.get(email="test@example.com")
        assert user.place == self._default_library.places[0]

        # welcome email sent
        assert len(mail.outbox) == 1
        assert (
            mail.outbox[0].subject
            == f"{self._default_library.name}: Welcome to the Palace App"
        )
        assert "Your account will not be activated until" in mail.outbox[0].body

    def test_card_request_bad_data(self):
        c = Client()

        # Prime the session
        self.do_library_card_signup_flow(c)

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
                place=12,  # A random place id
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
        errors = ["This field is required."]
        for field in expected_errors_fields:
            self.assertFormError(
                resp.context["form"],
                field,
                (
                    errors + ["First name is mandatory"]
                    if field == "first_name"
                    else errors
                ),
            )

    def test_card_request_no_patron_address(self):
        c = Client()

        library = self.create_library(patron_address_mandatory=False)
        # Prime the session
        self.do_library_card_signup_flow(c, library=library)

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

    def test_card_request_email_no_duplicates(self):
        user = self.create_user(self._default_library, "TEST@t.co")
        c = Client()

        library = self.create_library(patron_address_mandatory=False)
        # Prime the session
        self.do_library_card_signup_flow(c, library=library)

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
        installed_apps.remove("django_recaptcha")
        apps.set_installed_apps(installed_apps)

        new_apps = [ac.name for ac in apps.get_app_configs()]
        assert "django_recaptcha" not in new_apps
        self.test_card_request(with_captcha=False)
        apps.unset_installed_apps()

    def test_card_invalid_email_domain(self):
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
            place=12,  # a random places id
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

    def test_age_verification(self):
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

    def test_survey_consent(self):
        library = self._default_library
        library.has_survey_consent = True
        library.save()

        client = Client()
        self.do_library_card_signup_flow(client, library)

        post_dict = self._get_card_request_data(library, "test@test.test")

        resp = client.post(
            f"/account/library_card_request/?identifier={library.identifier}",
            post_dict,
        )
        user = CustomUser.objects.filter(email="test@test.test").first()
        consents = UserConsent.objects.filter(user=user).all()

        assert resp.status_code == 302
        assert len(consents) == 1
        consent = consents[0]
        assert consent.type == RequestLibraryCardForm.CONSENT_TYPE.value
        assert consent.method == RequestLibraryCardForm.CONSENT_METHOD.value
        assert consent.timestamp.date() == datetime.today().date()

    def test_survey_no_consent(self):
        library = self._default_library
        library.has_survey_consent = True
        library.save()

        client = Client()
        self.do_library_card_signup_flow(client, library)
        post_dict = self._get_card_request_data(library, "test@test.test")
        del post_dict["consent"]

        resp = client.post(
            f"/account/library_card_request/?identifier={library.identifier}",
            post_dict,
        )

        assert resp.status_code == 302
        user = CustomUser.objects.filter(email="test@test.test").first()
        # no consent was recorded
        assert UserConsent.objects.filter(user=user).count() == 0

    def test_form_survey_presence(self):
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

        form = RequestLibraryCardForm(instance=view.model)
        consent = form.fields["consent"]
        assert consent.disabled == True
        assert consent.initial == None
        assert type(consent.widget) == consent.hidden_widget

        view.model.library.has_survey_consent = True
        form = RequestLibraryCardForm(instance=view.model)
        consent = form.fields["consent"]
        assert consent.disabled == False
        assert consent.initial == "on"
        assert type(consent.widget) != consent.hidden_widget


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
