import json
import urllib

from django.conf import settings


class Geolocalize:
    @staticmethod
    def get_user_location(latitude, longitude):
        print("Geolocalize get_user_location")
        try:
            result = Geolocalize._lookup_position(latitude, longitude)
            print("get_user_location result", result)
            return json.loads(result)
        except Exception as err:
            print(err)
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
        print("url", url)
        contents = urllib.request.urlopen(url).read()
        return contents
