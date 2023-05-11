import json
from unittest import mock

from django.conf import settings

from tests.base import BaseUnitTest
from virtual_library_card.geoloc import Geolocalize


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

    @mock.patch("virtual_library_card.geoloc.urllib")
    def test_search_for_places(self, mock_urllib):
        return_value = {"results": [{"name": "New Mexico", "recordType": "state"}]}

        mock_urllib.request.urlopen().read = mock.MagicMock(
            return_value=json.dumps(return_value)
        )
        mock_urllib.request.urlopen().status = 200

        query = "new mex"
        response, status = Geolocalize.search_for_places(query)

        assert status == 200
        assert response == return_value
