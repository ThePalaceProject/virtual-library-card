import json
import re
import urllib

from django.conf import settings
from smartystreets_python_sdk import ClientBuilder, StaticCredentials, exceptions
from smartystreets_python_sdk.us_street import Lookup

from virtual_library_card.logging import log


class AddressChecker:
    POSTAL_ADDRESS_API = 1
    ZIP_CODE_API = 2

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
    def is_valid_zipcode(city, state, zip):
        # Keep only the numerical first half of a zipcode
        # that MAY have +'s or -'s, smarty streets does not accept such zips
        match: re.Match = re.match(r"^([0-9]{3,}).*", zip)
        if match is not None and len(match.groups()) > 0:
            zip = match.groups()[0]

        lookup: Lookup = Lookup(city=city, state=state, zipcode=zip)
        client = AddressChecker._set_client(api_type=AddressChecker.ZIP_CODE_API)
        try:
            client.send_lookup(lookup)
        except exceptions.SmartyException as err:
            log.error(f"Zipcode validation error {err}")
            return False

        zipcodes = lookup.result.zipcodes
        cities = lookup.result.cities
        return (
            len(zipcodes) > 0
            and zipcodes[0].zipcode == zip
            and len(cities) > 0
            and cities[0].city == city
            and cities[0].state_abbreviation == state
        )

    @staticmethod
    def get_user_location(latitude, longitude):
        try:
            result = AddressChecker._lookup_position(latitude, longitude)
            return json.loads(result)
        except exceptions.SmartyException as err:
            log.error(f"Get user location error {err}")
        return None

    @staticmethod
    def _set_client(api_type=POSTAL_ADDRESS_API):
        auth_id = settings.SMARTY_AUTH_ID
        auth_token = settings.SMARTY_AUTH_TOKEN

        credentials = StaticCredentials(auth_id, auth_token)
        if api_type == AddressChecker.POSTAL_ADDRESS_API:
            client = ClientBuilder(credentials).build_us_street_api_client()
        elif api_type == AddressChecker.ZIP_CODE_API:
            client = ClientBuilder(credentials).build_us_zipcode_api_client()
        else:
            raise Exception("Unknown API type referenced")

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
            log.error(f"_run.send_lookup error {err}")
            return

        result = lookup.result

        if not result:
            log.debug("No candidates. This means the address is not valid.")
            return

        first_candidate = result[0]
        log.debug("Address is valid. (There is at least one candidate)\n")
        log.debug("ZIP Code: " + first_candidate.components.zipcode)
        log.debug("County: " + first_candidate.metadata.county_name)
        log.debug("Latitude: {}".format(first_candidate.metadata.latitude))
        log.debug("Longitude: {}".format(first_candidate.metadata.longitude))
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
        log.debug(f"_lookup_position url: {url}")
        contents = urllib.request.urlopen(url).read()
        return contents
