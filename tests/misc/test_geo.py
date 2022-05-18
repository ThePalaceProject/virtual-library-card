import json
from unittest import mock

from django.conf import settings
from smartystreets_python_sdk.exceptions import SmartyException

from tests.base import BaseUnitTest
from virtual_library_card.geoloc import Geolocalize
from virtual_library_card.location_utils import LocationUtils
from virtual_library_card.smarty_streets import AddressChecker


class TestGeolocalize(BaseUnitTest):
    @mock.patch("virtual_library_card.geoloc.urllib")
    def test_get_user_location(self, mock_urllib):
        location_value = {"data": "somedata"}
        mock_urllib.request.urlopen().read = mock.MagicMock(
            return_value=json.dumps(location_value)
        )

        response = Geolocalize.get_user_location("10", "10")
        assert response == location_value

        # Test exception case
        mock_urllib.request.urlopen().read.side_effect = Exception("An exception")
        response = Geolocalize.get_user_location("10", "10")
        assert response == None

    @mock.patch("virtual_library_card.geoloc.urllib")
    def test_lookup_position(self, mock_urllib):
        return_value = "areturnvalue"
        mock_urllib.request.urlopen = mock.MagicMock()
        mock_urllib.request.urlopen().read = mock.MagicMock(return_value=return_value)
        response = Geolocalize._lookup_position("10", "10")

        expected_url = f"http://www.mapquestapi.com/geocoding/v1/reverse?key={settings.MARQUEST_AUTH_ID}&location=10,10&outFormat=json&thumbMaps=false"
        assert (
            mock_urllib.request.urlopen.call_count == 2
        )  # called once when setting up urlopen().read mock object
        assert mock_urllib.request.urlopen.call_args[0][0] == expected_url
        assert response == return_value


class TestLocationUtils(BaseUnitTest):
    def test_get_library_state_name(self):
        library = self.create_library(us_states=["NY", "AL"])
        # returns the first state (alphabetical order) (we shouldn't have weird behaviour like this)
        assert LocationUtils.get_library_state_name(library) == "Alabama"

        library = self.create_library(us_states=["AX", "NY"])
        # returns the first valid state name
        assert LocationUtils.get_library_state_name(library) == "New York"


class TestAddressChecker(BaseUnitTest):
    @mock.patch("virtual_library_card.smarty_streets.StaticCredentials")
    @mock.patch("virtual_library_card.smarty_streets.ClientBuilder")
    def test_set_client(self, mock_builder, mock_credentials):
        client = AddressChecker._set_client()

        assert mock_credentials.call_count == 1
        assert mock_credentials.call_args[0] == (
            settings.SMARTY_AUTH_ID,
            settings.SMARTY_AUTH_TOKEN,
        )

        assert mock_builder.call_count == 1
        assert mock_builder.call_args[0] == (mock_credentials(),)
        assert mock_builder().build_us_street_api_client.call_count == 1
        assert mock_builder().build_us_street_api_client() == client

    @mock.patch("virtual_library_card.smarty_streets.AddressChecker._set_client")
    def test_run(self, mock_client):
        lookup = mock.MagicMock()
        result_value = mock.MagicMock()
        lookup.result.__getitem__.return_value = result_value

        result = AddressChecker._run(lookup)

        assert mock_client.call_count == 1
        assert mock_client().send_lookup.call_count == 1
        assert mock_client().send_lookup.call_args[0] == (lookup,)
        assert result == result_value

        lookup.result = None
        assert AddressChecker._run(lookup) == None

        lookup.result = []
        assert AddressChecker._run(lookup) == None

    @mock.patch("virtual_library_card.smarty_streets.Lookup")
    def test_create_lookup(self, mock_lookup):
        args = (
            "first_name",
            "last_name",
            "street_address_line1",
            "street_address_line2",
            "city",
            "us_state",
            "zip",
        )

        lookup = AddressChecker._create_lookup(*args)

        assert lookup == mock_lookup()
        assert lookup.addressee == "first_name last_name"
        assert lookup.street == "street_address_line1"
        assert lookup.street2 == "street_address_line2"
        assert lookup.state == "us_state"
        assert lookup.zipcode == "zip"
        assert lookup.candidates == 3
        assert lookup.match == "Invalid"

    @mock.patch("virtual_library_card.smarty_streets.urllib")
    def test_lookup_position(self, mock_urllib):
        # mock_urllib.request.urlopen = mock.MagicMock
        result = AddressChecker._lookup_position("10", "10")
        assert mock_urllib.request.urlopen.call_count == 1
        assert mock_urllib.request.urlopen.call_args[0] == (
            f"https://us-reversegeo.api.smartystreets.com/lookup?auth-id={settings.SMARTY_AUTH_ID}&auth-token={settings.SMARTY_AUTH_TOKEN}"
            + "&latitude=10&longitude=10&measurement=meters&results=1",
        )
        assert result == mock_urllib.request.urlopen().read()

    @mock.patch("virtual_library_card.smarty_streets.AddressChecker._lookup_position")
    def test_get_user_location(self, mock_lookup):
        result_value = dict(value="value")
        mock_lookup.return_value = json.dumps(result_value)
        result = AddressChecker.get_user_location("10", "10")
        assert result == result_value

        mock_lookup.side_effect = SmartyException()
        result = AddressChecker.get_user_location("10", "10")
        assert result == None

    @mock.patch("virtual_library_card.smarty_streets.AddressChecker._create_lookup")
    @mock.patch("virtual_library_card.smarty_streets.AddressChecker._run")
    def test_is_valid_postal_address(self, mock_run, mock_create_lookup):
        args = ("first_name", "last_name", "line1", "line2", "city", "state", "zip")
        result = AddressChecker.is_valid_postal_address(*args)

        assert mock_create_lookup.call_count == 1
        assert mock_create_lookup.call_args[0] == args

        assert mock_run.call_count == 1
        assert mock_run.call_args[0] == (mock_create_lookup(),)

        assert result == True

        # False response
        mock_run.return_value = None
        assert AddressChecker.is_valid_postal_address(*args) == False
