from typing import Literal

from virtuallibrarycard.models import Library, Place


class LibraryRules:
    @classmethod
    def validate_user_address_fields(
        cls,
        library: Library,
        city: str | None = None,
        county: str | None = None,
        state: str | None = None,
        country: str | None = None,
    ) -> Place | Literal[False]:
        """Validate whether the given address fields are valid for a user that would signup for a given library
        - Country, State or City, at least one must be within the list of places of the library
        """

        places = library.places

        # For every place the library defines
        # check to see if it fits with the address provided for the user
        for place in places:
            if cls._place_hierarchy_match(
                place, city=city, county=county, state=state, country=country
            ):
                return place

        return False

    @classmethod
    def _place_hierarchy_match(
        cls,
        place: Place,
        city: str | None = None,
        county: str | None = None,
        state: str | None = None,
        country: str | None = None,
    ) -> bool:
        """Test from the current place all the way to the last parent available.
        All levels of the place hierarchy MUST match even if the value isn't provided in the keyword args.
        """
        match_types = {
            Place.Types.COUNTRY: country,
            Place.Types.STATE: state,
            Place.Types.PROVINCE: state,
            Place.Types.CITY: city,
            Place.Types.COUNTY: county,
        }

        while True:
            match_abbr = match_types.get(place.type)

            if place.check_str == match_abbr:
                # No more parents. everything matched!
                if not place.parent:
                    return True
                # Has a parent, match the parent as well
                place = place.parent
            else:
                return False
