import json
import urllib

from django.conf import settings

from virtual_library_card.logging import log


class Geolocalize:
    @staticmethod
    def get_user_location(latitude, longitude):
        try:
            result = Geolocalize._lookup_position(latitude, longitude)
            return json.loads(result)
        except Exception as err:
            log.error(f"Get user location error: {err}")
        return None

    @staticmethod
    def _lookup_position(latitude, longitude):
        root_url = "http://www.mapquestapi.com/geocoding/v1/reverse?"
        params_url = (
            "key="
            + settings.MARQUEST_AUTH_ID
            + "&location="
            + latitude
            + ","
            + longitude
            + "&outFormat=json&thumbMaps=false"
        )
        url = root_url + params_url
        contents = urllib.request.urlopen(url).read()
        return contents
