from virtuallibrarycard.models import Library, Place


class LibraryRules:
    @classmethod
    def validate_user_address_fields(
        cls,
        library: Library,
        city: str = None,
        county: str = None,
        state: str = None,
        country: str = None,
    ) -> bool:
        """Validate whether the given address fields are valid for a user that would signup for a given library
        - Country, State or City, atleast one must within the list of places of the library
        """

        places = library.places
        match_types = {
            Place.Types.COUNTRY: country,
            Place.Types.STATE: state,
            Place.Types.PROVINCE: state,
            Place.Types.CITY: city,
            Place.Types.COUNTY: county,
        }

        # For every place the library defines
        # check to see if it fits with the address provided for the user
        for place in places:
            # Get the appropriate string to match against
            match_abbr = match_types.get(place.type)
            if not match_abbr:
                continue
            if match_abbr == place.check_str:
                return True

        return False
