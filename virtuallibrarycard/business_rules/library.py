from attr import define

from virtual_library_card.smarty_streets import AddressChecker
from virtuallibrarycard.models import Library, Place


@define
class UserAddressValidationResult:
    state_valid: bool = True
    zip_valid: bool = True


class LibraryRules:
    @classmethod
    def validate_user_address_fields(
        cls, library: Library, zip: str = None, city: str = None, place: str = None
    ) -> UserAddressValidationResult:
        """Validate whether the given address fields are valid for a user that would signup for a given library
        - State must be within the list of states allowed in the library
        - Zipcode must be valid for the city provided, if provided"""
        result = UserAddressValidationResult()
        countries = map(
            lambda p: p.abbreviation, Place.objects.filter(type=Place.Types.COUNTRY)
        )
        places = library.get_places()
        # If the library place is a country then we don't validate the state
        # When VLC will service more than the US, then change this to check parent country of the state
        if set(countries).intersection(places):
            pass  # state_valid is True by default
        elif place and place not in places:
            result.state_valid = False

        if library.patron_address_mandatory and zip and city and place:
            result.zip_valid = AddressChecker.is_valid_zipcode(city, place, zip)

        return result
