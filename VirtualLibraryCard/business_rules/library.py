from attr import define

from virtual_library_card.smarty_streets import AddressChecker
from VirtualLibraryCard.models import Library


@define
class UserAddressValidationResult:
    us_state_valid: bool = True
    zip_valid: bool = True


class LibraryRules:
    @classmethod
    def validate_user_address_fields(
        cls, library: Library, zip=None, city=None, us_state=None
    ) -> UserAddressValidationResult:
        """Validate whether the given address fields are valid for a user that would signup for a given library
        - State must be within the list of states allowed in the library
        - Zipcode must be valid for the city provided, if provided"""
        result = UserAddressValidationResult()
        if us_state and not library.allow_all_us_states:
            if us_state not in library.get_us_states():
                result.us_state_valid = False

        if library.patron_address_mandatory and zip and city and us_state:
            result.zip_valid = AddressChecker.is_valid_zipcode(city, us_state, zip)

        return result
