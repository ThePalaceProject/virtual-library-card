from unittest import mock

from base import BaseUnitTest
from django.test import Client


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
                            "postalCode": "998867",
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
