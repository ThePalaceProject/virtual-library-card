import json
import urllib

from django.conf import settings

from virtual_library_card.logging import log


class Geolocalize:
    @staticmethod
    def get_user_location(latitude, longitude):
        try:
            result = Geolocalize._lookup_position(latitude, longitude)
            result = json.loads(result)
            PostProcess.mapquest_reverse_geocode(result)
            return result
        except Exception as err:
            log.error(f"Get user location error: {err}")
        return None

    @staticmethod
    def _lookup_position(latitude, longitude):
        root_url = "http://www.mapquestapi.com/geocoding/v1/reverse?"
        params_url = (
            "key="
            + settings.MAPQUEST_API_KEY
            + "&location="
            + latitude
            + ","
            + longitude
            + "&outFormat=json&thumbMaps=false"
        )
        url = root_url + params_url
        contents = urllib.request.urlopen(url).read()
        return contents

    @staticmethod
    def search_for_places(query):
        root_url = "https://www.mapquestapi.com/search/v3/prediction?"

        # We are searching only for administrative areas in US and Canada.
        collection = "adminArea"
        country_code = "US,CA"

        parameters = {
            "key": settings.MAPQUEST_API_KEY,
            "collection": collection,
            "countryCode": country_code,
            "q": query,
        }

        params_url = urllib.parse.urlencode(parameters)

        url = root_url + params_url
        response = urllib.request.urlopen(url)

        contents = json.loads(response.read())
        status = response.status

        return contents, status


class PostProcess:
    @classmethod
    def mapquest_reverse_geocode(cls, data: dict) -> None:
        """Some mapquest data is different than what we expect the hierarchy to be.
        Eg. US territories are treated as countries on their own, they should be under the US Country.
        """
        if (
            len(data.get("results", [])) < 1
            or len(locations := data["results"][0].get("locations", [])) < 1
        ):
            return

        # List[dict, dict]: [What should we match against, What should we change]
        changes: list[list[dict, dict]] = [
            [dict(adminArea1="AS"), dict(adminArea1="US", adminArea3="AS")],
            [dict(adminArea1="GU"), dict(adminArea1="US", adminArea3="GU")],
            [dict(adminArea1="PR"), dict(adminArea1="US", adminArea3="PR")],
            [dict(adminArea1="VI"), dict(adminArea1="US", adminArea3="VI")],
            [dict(adminArea1="MP"), dict(adminArea1="US", adminArea3="MP")],
        ]

        location: dict = locations[0]
        for [query, change] in changes:
            for key, value in query.items():
                # All items must match else we break out of the loop
                if location[key] != value:
                    break
            else:
                # All matched! We can update the data and break out
                location.update(change)
                break
