import json
from unittest import mock

from django.conf import settings
from smartystreets_python_sdk.exceptions import SmartyException

from tests.base import BaseUnitTest
from virtual_library_card.geoloc import Geolocalize
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

    @mock.patch("virtual_library_card.smarty_streets.Lookup")
    @mock.patch("virtual_library_card.smarty_streets.AddressChecker._set_client")
    def test_is_valid_zipcode(
        self, mock_client: mock.MagicMock, mock_lookup: mock.MagicMock
    ):

        mock_result = mock.MagicMock()
        mock_result.result.zipcodes.__len__.return_value = 1
        mock_result.result.cities.__len__.return_value = 1
        mock_result.result.zipcodes.__getitem__.return_value.zipcode = "zip"
        mock_result.result.cities.__getitem__.return_value.city = "city"
        mock_result.result.cities.__getitem__.return_value.state_abbreviation = "state"
        mock_lookup.return_value = mock_result

        args = ("city", "state", "zip")
        result = AddressChecker.is_valid_zipcode(*args)

        assert mock_lookup.call_count == 1
        assert mock_lookup.call_args_list[0].kwargs == dict(
            city="city", state="state", zipcode="zip"
        )

        assert mock_client.call_count == 1
        assert mock_client.call_args_list[0].kwargs == dict(
            api_type=AddressChecker.ZIP_CODE_API
        )

        assert mock_client().send_lookup.call_count == 1
        assert mock_client().send_lookup.call_args[0] == (mock_lookup(),)

        assert result == True

    @mock.patch("virtual_library_card.smarty_streets.Lookup")
    @mock.patch("virtual_library_card.smarty_streets.AddressChecker._set_client")
    def test_is_valid_zipcode_zip_re(
        self, mock_client: mock.MagicMock, mock_lookup: mock.MagicMock
    ):
        args = ("city", "state", "123123-1234")
        AddressChecker.is_valid_zipcode(*args)
        assert mock_lookup.call_count == 1
        assert mock_lookup.call_args == mock.call(
            city="city", state="state", zipcode="123123"
        )

    @mock.patch("virtual_library_card.smarty_streets.Lookup")
    @mock.patch("virtual_library_card.smarty_streets.AddressChecker._set_client")
    def test_is_valid_zipcode_exc(
        self, mock_client: mock.MagicMock, mock_lookup: mock.MagicMock
    ):
        mock_client.return_value.send_lookup.side_effect = SmartyException()
        args = ("city", "state", "zip")
        result = AddressChecker.is_valid_zipcode(*args)
        assert result == False
        # len(lookup.result.zipcodes) was not called
        assert mock_lookup.return_value.result.zipcodes.__len__.call_count == 0

    @mock.patch("virtual_library_card.smarty_streets.Lookup")
    @mock.patch("virtual_library_card.smarty_streets.AddressChecker._set_client")
    def test_is_valid_zipcode_no_match(
        self, mock_client: mock.MagicMock, mock_lookup: mock.MagicMock
    ):
        mock_result = mock.MagicMock()
        mock_result.result.zipcodes.__len__.return_value = 1
        mock_result.result.cities.__len__.return_value = 1
        mock_result.result.zipcodes.__getitem__.return_value.zipcode = "zip"
        mock_result.result.cities.__getitem__.return_value.city = "city"
        mock_result.result.cities.__getitem__.return_value.state_abbreviation = "state"
        mock_lookup.return_value = mock_result

        args = ("city", "state", "zip")

        mock_result.result.zipcodes.__getitem__.return_value.zipcode = "notzip"
        result = AddressChecker.is_valid_zipcode(*args)
        assert result == False

        mock_result.result.zipcodes.__getitem__.return_value.zipcode = "zip"
        mock_result.result.cities.__getitem__.return_value.city = "notcity"
        result = AddressChecker.is_valid_zipcode(*args)
        assert result == False

        mock_result.result.cities.__getitem__.return_value.city = "city"
        mock_result.result.cities.__getitem__.return_value.state_abbreviation = (
            "notstate"
        )
        result = AddressChecker.is_valid_zipcode(*args)
        assert result == False

        mock_result.result.zipcodes.__len__.return_value = 0
        mock_result.result.cities.__getitem__.return_value.state_abbreviation = "state"
        result = AddressChecker.is_valid_zipcode(*args)
        assert result == False

        mock_result.result.zipcodes.__len__.return_value = 1
        mock_result.result.cities.__len__.return_value = 0
        result = AddressChecker.is_valid_zipcode(*args)
        assert result == False

        # Everything back to normal still works
        mock_result.result.cities.__len__.return_value = 1
        result = AddressChecker.is_valid_zipcode(*args)
        assert result == True
