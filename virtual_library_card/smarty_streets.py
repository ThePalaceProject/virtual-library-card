import json
import urllib

from django.conf import settings
from smartystreets_python_sdk import ClientBuilder, StaticCredentials, exceptions
from smartystreets_python_sdk.us_street import Lookup


class AddressChecker:
    @staticmethod
    def is_valid_postal_address(
        first_name,
        last_name,
        street_address_line1,
        street_address_line2,
        city,
        us_state,
        zip,
    ):
        lookup: Lookup = AddressChecker._create_lookup(
            first_name,
            last_name,
            street_address_line1,
            street_address_line2,
            city,
            us_state,
            zip,
        )
        first_candidate = AddressChecker._run(lookup)
        if first_candidate:
            return True
        return False

    @staticmethod
    def get_user_location(latitude, longitude):
        print("get_user_location")
        try:
            result = AddressChecker._lookup_position(latitude, longitude)
            print("get_user_location result", result)
            return json.loads(result)
        except exceptions.SmartyException as err:
            print(err)
        return None

    @staticmethod
    def _set_client():
        auth_id = settings.SMARTY_AUTH_ID
        auth_token = settings.SMARTY_AUTH_TOKEN
        credentials = StaticCredentials(auth_id, auth_token)
        client = ClientBuilder(credentials).build_us_street_api_client()
        # client = ClientBuilder(credentials).with_custom_header({'User-Agent': 'smartystreets (python@0.0.0)', 'Content-Type': 'application/json'}).build_us_street_api_client()
        # client = ClientBuilder(credentials).with_proxy('localhost:8080', 'user','password').build_us_street_api_client()
        # Uncomment the line above to try it with a proxy instead
        return client

    @staticmethod
    def _run(lookup: Lookup):
        client = AddressChecker._set_client()
        try:
            client.send_lookup(lookup)
        except exceptions.SmartyException as err:
            print(err)
            return

        result = lookup.result

        if not result:
            print("No candidates. This means the address is not valid.")
            return

        first_candidate = result[0]
        print("Address is valid. (There is at least one candidate)\n")
        print("ZIP Code: " + first_candidate.components.zipcode)
        print("County: " + first_candidate.metadata.county_name)
        print("Latitude: {}".format(first_candidate.metadata.latitude))
        print("Longitude: {}".format(first_candidate.metadata.longitude))
        return first_candidate

    @staticmethod
    def _create_lookup(
        first_name,
        last_name,
        street_address_line1,
        street_address_line2,
        city,
        us_state,
        zip,
    ):
        lookup = Lookup()
        lookup.addressee = first_name + " " + last_name
        lookup.street = street_address_line1
        lookup.street2 = street_address_line2
        lookup.city = city
        lookup.state = us_state
        lookup.zipcode = zip
        lookup.candidates = 3
        lookup.match = "Invalid"
        return lookup

    @staticmethod
    def _lookup_position(latitude, longitude):
        root_url = "https://us-reversegeo.api.smartystreets.com/lookup?"
        params_url = (
            "auth-id="
            + settings.SMARTY_AUTH_ID
            + "&auth-token="
            + settings.SMARTY_AUTH_TOKEN
            + "&latitude="
            + latitude
            + "&longitude="
            + longitude
            + "&measurement=meters&results=1"
        )
        url = root_url + params_url
        print("url", url)
        contents = urllib.request.urlopen(url).read()
        return contents
