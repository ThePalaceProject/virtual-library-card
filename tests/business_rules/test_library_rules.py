from tests.base import BaseUnitTest
from virtuallibrarycard.business_rules.library import LibraryRules
from virtuallibrarycard.models import Library, LibraryPlace, Place


class TestLibraryRules(BaseUnitTest):
    def test_validate_address_valid_state(self):
        library = self.create_library(places=["NY", "AL"])
        result = LibraryRules.validate_user_address_fields(library, state="AL")
        assert result is True

    def test_validate_address_invalid_state(self):
        library = self.create_library(places=["NY", "AL"])
        result = LibraryRules.validate_user_address_fields(library, state="HI")
        assert result is False

    def test_valid_country(self):
        library: Library = self.create_library(places=[])
        LibraryPlace(library=library, place=Place.objects.get(name="Canada")).save()
        # State doesn't matter
        result = LibraryRules.validate_user_address_fields(
            library, state="AL", country="CA"
        )
        assert result is True

    def test_invalid_country(self):
        library: Library = self.create_library(places=[])
        LibraryPlace(library=library, place=Place.objects.get(name="Canada")).save()
        # State doesn't matter
        result = LibraryRules.validate_user_address_fields(
            library, state="AL", country="US"
        )
        assert result is False

    def test_invalid_state_and_country(self):
        library: Library = self.create_library(places=["AL"])
        LibraryPlace(library=library, place=Place.objects.get(name="Canada")).save()
        result = LibraryRules.validate_user_address_fields(
            library, state="KS", country="US"
        )
        assert result is False

    def test_valid_city(self):
        toronto = Place(
            name="Toronto", abbreviation="_TO", type=Place.Types.CITY, external_id="_TO"
        ).save()
        library: Library = self.create_library(places=["_TO"])
        result = LibraryRules.validate_user_address_fields(
            library, state="Anything", city="Toronto"
        )
        assert result is True

    def test_invalid_city(self):
        toronto = Place(
            name="Toronto", abbreviation="_TO", type=Place.Types.CITY, external_id="_TO"
        ).save()
        vancouver = Place(
            name="Vancouver",
            abbreviation="_VA",
            type=Place.Types.CITY,
            external_id="_VA",
        ).save()
        library: Library = self.create_library(places=["_VA"])
        result = LibraryRules.validate_user_address_fields(
            library, state="Anything", city="_TO"
        )
        assert result is False

    def test_all_negatives_when_required(self):
        toronto = Place(
            name="Toronto", abbreviation="_TO", type=Place.Types.CITY, external_id="_TO"
        ).save()
        # Country, state and city are all present in this library
        library: Library = self.create_library(places=["_TO", "NY", "US"])
        result = LibraryRules.validate_user_address_fields(
            library, state="NOT_NY", city="NOT_TO", country="NOT_US"
        )
        assert result is False
