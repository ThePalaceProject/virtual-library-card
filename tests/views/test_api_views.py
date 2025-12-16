import json
from datetime import UTC, datetime, timedelta
from unittest import mock

from django.core.handlers.wsgi import WSGIRequest
from django.test import RequestFactory

from tests.base import BaseUnitTest
from virtuallibrarycard.models import CustomUser, LibraryCard
from virtuallibrarycard.views.views_api import (
    PinTestPOSTViewSet,
    PinTestViewSet,
    PlaceSearchAheadView,
    UserLibraryCardViewSet,
)


class TestPinTestPOSTViewSet(BaseUnitTest):
    def _setup_view(
        self, card: LibraryCard, user: CustomUser, password: str
    ) -> PinTestPOSTViewSet:
        user.set_password(password)
        user.save()
        request: WSGIRequest = RequestFactory().post(
            "/pintest", data=dict(number="1234", pin="1234")
        )
        view = PinTestPOSTViewSet()
        view.setup(request)
        return view

    def test_bad_pin(self):
        password = "apassword"
        view = self._setup_view(self._default_card, self._default_user, password)
        view.request.data = {
            "number": self._default_card.number,
            "pin": f"{password}NOT",
        }
        response = view.post(view.request)

        assert response.data["RETCOD"] == 1
        assert response.data["ERRNUM"] == 4
        assert response.data["ERRMSG"] == "Invalid patron PIN"

    def test_bad_card(self):
        password = "apassword"
        view = self._setup_view(self._default_card, self._default_user, password)
        view.request.data = {
            "number": f"{self._default_card.number}xx",
            "pin": password,
        }
        response = view.post(view.request)

        assert response.data["RETCOD"] == 1
        assert response.data["ERRNUM"] == 1
        assert response.data["ERRMSG"] == "Requested record not found"

    def test_missing_card(self):
        password = "apassword"
        view = self._setup_view(self._default_card, self._default_user, password)
        view.request.data = {"pin": password}
        response = view.post(view.request)

        assert response.data["RETCOD"] == 1
        assert response.data["ERRNUM"] == 100000
        assert (
            response.data["ERRMSG"]
            == "Missing required parameter(s): 'number' and 'pin'"
        )

    def test_missing_pin(self):
        password = "apassword"
        view = self._setup_view(self._default_card, self._default_user, password)
        view.request.data = {"number": f"{self._default_card.number}"}
        response = view.post(view.request)

        assert response.data["RETCOD"] == 1
        assert response.data["ERRNUM"] == 100000
        assert (
            response.data["ERRMSG"]
            == "Missing required parameter(s): 'number' and 'pin'"
        )

    def test_api(self):
        password = "apassword"
        self._default_user.set_password(password)
        self._default_user.save()
        card = self._default_card

        response = self.client.post(
            f"/api/pintest", data={"number": card.number, "pin": password}
        )
        assert response.content == b"<HTML>\n<BODY>\nRETCOD=0<BR>\n</BODY>\n</HTML>"

        response = self.client.post(
            f"/PATRONAPI/pintest", data={"number": card.number, "pin": password}
        )
        assert response.content == b"<HTML>\n<BODY>\nRETCOD=0<BR>\n</BODY>\n</HTML>"

    def test_unverified_user(self):
        user = self.create_user(self._default_library, email_verified=False)
        card = self.create_library_card(user, self._default_library)
        password = "apassword"
        user.set_password(password)
        user.save()

        response = self.client.post(
            "/api/pintest", data={"number": card.number, "pin": password}
        )
        content = response.content.decode()
        assert "RETCOD=1" in content
        assert "ERRNUM=5" in content


class TestPinTestViewSet(BaseUnitTest):
    def _setup_view(
        self, card: LibraryCard, user: CustomUser, password: str
    ) -> PinTestViewSet:
        user.set_password(password)
        user.save()
        request: WSGIRequest = RequestFactory().get(
            f"/{card.number}/{password}/pintest"
        )
        view = PinTestViewSet()
        view.setup(request)
        return view

    def test_get_method(self):
        password = "apassword"
        view = self._setup_view(self._default_card, self._default_user, password)
        response = view.get(view.request, self._default_card.number, password)

        assert response.data["RETCOD"] == 0

    def test_bad_pin(self):
        password = "apassword"
        view = self._setup_view(self._default_card, self._default_user, password)
        response = view.get(view.request, self._default_card.number, password + "NOT")

        assert response.data["RETCOD"] == 1
        assert response.data["ERRNUM"] == 4
        assert response.data["ERRMSG"] == "Invalid patron PIN"

    def test_bad_card(self):
        password = "apassword"
        view = self._setup_view(self._default_card, self._default_user, password)
        response = view.get(view.request, self._default_card.number + "xx", password)

        assert response.data["RETCOD"] == 1
        assert response.data["ERRNUM"] == 1
        assert response.data["ERRMSG"] == "Requested record not found"

    def test_api(self):
        password = "apassword"
        self._default_user.set_password(password)
        self._default_user.save()
        card = self._default_card

        response = self.client.get(f"/api/{card.number}/{password}/pintest")
        assert response.content == b"<HTML>\n<BODY>\nRETCOD=0<BR>\n</BODY>\n</HTML>"

        response = self.client.get(f"/PATRONAPI/{card.number}/{password}/pintest")
        assert response.content == b"<HTML>\n<BODY>\nRETCOD=0<BR>\n</BODY>\n</HTML>"

    def test_unverified_user(self):
        user = self.create_user(self._default_library, email_verified=False)
        card = self.create_library_card(user, self._default_library)
        password = "apassword"
        user.set_password(password)
        user.save()

        response = self.client.get(f"/api/{card.number}/{password}/pintest")
        content = response.content.decode()
        assert "RETCOD=1" in content
        assert "ERRNUM=5" in content

    def test_post_method(self):
        user = self.create_user(self._default_library, email_verified=False)
        card = self.create_library_card(user, self._default_library)
        password = "apassword"
        user.set_password(password)
        user.save()

        response = self.client.post(f"/api/{card.number}/{password}/pintest")
        content = response.content.decode()
        assert "405 Method Not Allowed" in content


class TestUserLibraryCardViewSet(BaseUnitTest):
    def _setup_view(self, card: LibraryCard) -> UserLibraryCardViewSet:
        request: WSGIRequest = RequestFactory().get(f"/{card.number}/dump")
        view = UserLibraryCardViewSet()
        view.setup(request)
        return view

    def test_get(self):
        view = self._setup_view(self._default_card)
        response = view.get(view.request, self._default_card.number)

        assert "library_cards" in response.data
        assert len(response.data["library_cards"]) == 1
        data = response.data["library_cards"][0]
        assert data == self._default_card

    def test_bad_number(self):
        view = self._setup_view(self._default_card)
        response = view.get(view.request, self._default_card.number + "xx")

        assert response.data["ERRNUM"] == 1
        assert response.data["ERRMSG"] == "Requested record not found"

    def test_api(self):
        card = self.create_library_card(
            self._default_user,
            self._default_library,
            expiration_date=datetime.now(UTC) + timedelta(days=1),
        )

        expected = (
            f"<HTML>\n<BODY>\n"
            f"EXP DATE[p43]={card.expiration_date.strftime('%m-%d-%y')}<BR>\n"
            f"HOME LIBR[p53]={card.library.identifier}<BR>"
            f"\nCREATED[p83]={card.created.strftime('%m-%d-%y')}<BR>"
            f"\nPATRN NAME[pn]={card.user.get_smart_name()}<BR>"
            f"\nP BARCODE[pb]={card.number}<BR>\n</BODY>\n</HTML>"
        )

        response = self.client.get(f"/PATRONAPI/{card.number}/dump")
        assert response.content == expected.encode()

        response = self.client.get(f"/api/{card.number}/dump")
        assert response.content == expected.encode()


class TestPlaceSearchAheadView(BaseUnitTest):
    EXAMPLE_GEOLOC_SEARCH_RESPONSE_VALUE = {
        "results": [
            {
                "collection": ["adminArea"],
                "displayString": "New York, NY, United States",
                "language": "en",
                "id": "mqId:282040974",
                "name": "New York",
                "place": {
                    "geometry": {"coordinates": [-74.00712, 40.71453], "type": "Point"},
                    "properties": {
                        "country": "United States",
                        "countryCode": "US",
                        "state": "New York",
                        "stateCode": "NY",
                        "county": "New York",
                        "city": "New York",
                        "type": "city",
                    },
                    "type": "Feature",
                },
                "recordType": "city",
                "slug": "/us/ny/new-york",
            },
            {
                "collection": ["adminArea"],
                "displayString": "NJ, United States",
                "language": "en",
                "id": "mqId:282094985",
                "name": "New Jersey",
                "place": {
                    "geometry": {"coordinates": [-74.75942, 40.21789], "type": "Point"},
                    "properties": {
                        "country": "United States",
                        "countryCode": "US",
                        "state": "New Jersey",
                        "stateCode": "NJ",
                        "type": "state",
                    },
                    "type": "Feature",
                },
                "recordType": "state",
                "slug": "/us/nj",
            },
        ],
        "request": {
            "q": "new",
            "collection": ["adminArea"],
            "limit": 2,
            "countryCode": ["US", "CA"],
        },
    }

    def test_get_list_edge_cases(self):
        view = PlaceSearchAheadView()

        # If there is no q (query) we get an empty list back.
        view.q = None
        assert [] == view.get_list()

        # Length of query item must be between 2 and 100 chars.
        view.q = "a"
        assert [] == view.get_list()

        view.q = "a" * 101
        assert [] == view.get_list()

    @mock.patch("virtual_library_card.geoloc.urllib")
    def test_get_list(self, mock_urllib):
        view = PlaceSearchAheadView()
        view.q = "new"

        mock_urllib.request.urlopen().read = mock.MagicMock(
            return_value=json.dumps(self.EXAMPLE_GEOLOC_SEARCH_RESPONSE_VALUE)
        )
        mock_urllib.request.urlopen().status = 200

        expected_output = [
            {
                "id": "New Jersey|mqId:282094985",
                "name": "New Jersey",
                "text": "NJ, United States | state",
                "type": "state",
                "parents": [{"type": "country", "value": "United States"}],
            },
            {
                "id": "New York|mqId:282040974",
                "name": "New York",
                "text": "New York, NY, United States | city",
                "type": "city",
                "parents": [
                    {"type": "county", "value": "New York"},
                    {"type": "state", "value": "New York"},
                    {"type": "country", "value": "United States"},
                ],
            },
        ]

        assert expected_output == sorted(
            view.get_list(), key=lambda place: place["name"]
        )

    @mock.patch("virtual_library_card.geoloc.urllib")
    def test_get(self, mock_urllib):
        mock_urllib.request.urlopen().read = mock.MagicMock(
            return_value=json.dumps(self.EXAMPLE_GEOLOC_SEARCH_RESPONSE_VALUE)
        )
        mock_urllib.request.urlopen().status = 200

        # Only admins can access this endpoint.
        response = self.client.get(f"/place/search", data={"q": "new"})
        assert response.status_code == 403

        self.super_user = CustomUser.objects.create_superuser(
            "test@admin.com", "password"
        )
        self.client.force_login(self.super_user)

        response = self.client.get(f"/place/search", data={"q": "new"})
        response_data = json.loads(response.content.decode())

        assert response.status_code == 200
        assert "results" in response_data

        results = response_data["results"]

        # Results contain 2 items returned by Mapquest API plus additional one that is used for 'create' option in the
        # dropdown in the admin UI. That 'create' option makes it possible to add Place that is not found by the API.
        assert len(results) == 3

        text_results = sorted([result["text"] for result in results])
        assert [
            'Create "new"',
            "NJ, United States | state",
            "New York, NY, United States | city",
        ] == text_results

    def test_extract_places_to_list(self):
        # No results leads to an empty list.
        no_results = {"results": []}
        assert [] == PlaceSearchAheadView.extract_places_to_list(no_results)

        # Place types that are not supported are removed from the list.
        city_and_a_neighborhood = {
            "results": [
                {
                    "name": "Bronzeville",
                    "recordType": "neighborhood",
                    "id": "mqId:352584189",
                    "displayString": "Bronzeville, Chicago, IL, United States",
                    "place": {
                        "properties": {
                            "country": "United States",
                            "type": "neighborhood",
                        }
                    },
                },
                {
                    "name": "Bronson",
                    "recordType": "city",
                    "id": "mqId:282028197",
                    "displayString": "Bronson, FL, United States",
                    "place": {
                        "properties": {"country": "United States", "type": "city"}
                    },
                },
            ]
        }

        extracted_places = PlaceSearchAheadView.extract_places_to_list(
            city_and_a_neighborhood
        )

        # We are left with only Bronson.
        assert len(extracted_places) == 1
        assert extracted_places[0]["type"] == "city"
        assert extracted_places[0]["name"] == "Bronson"

    def test_create_parents_list(self):
        vancouver_place_properties = {
            "country": "Canada",
            "countryCode": "CA",
            "state": "British Columbia",
            "stateCode": "BC",
            "county": "Metro Vancouver",
            "city": "Vancouver",
            "type": "city",
        }
        expected_vancouver_parents = [
            {"type": "county", "value": "Metro Vancouver"},
            {"type": "province", "value": "British Columbia"},
            {"type": "country", "value": "Canada"},
        ]
        assert expected_vancouver_parents == PlaceSearchAheadView.create_parents_list(
            vancouver_place_properties
        )

        dallas_place_properties = {
            "country": "United States",
            "countryCode": "US",
            "state": "Texas",
            "stateCode": "TX",
            "county": "Dallas",
            "city": "Dallas",
            "type": "city",
        }
        expected_dallas_parents = [
            {"type": "county", "value": "Dallas"},
            {"type": "state", "value": "Texas"},
            {"type": "country", "value": "United States"},
        ]
        assert expected_dallas_parents == PlaceSearchAheadView.create_parents_list(
            dallas_place_properties
        )

    def test_create(self):
        # Method just returns the input variable.
        view = PlaceSearchAheadView()
        assert "string" == view.create("string")
