from importlib import import_module

import pytest
from django.apps import apps

from tests.base import BaseUnitTest
from virtuallibrarycard.models import LibraryStates


class TestPlaceMigration(BaseUnitTest):
    def _associate_us_states(self, library, us_states):
        for s in us_states:
            ls = LibraryStates(library=library, us_state=s)
            ls.save()

    def test_data_migration(self):
        """Test the LibraryStates DB migration.
        This test will start failing due to discrepancies in the models in the future sometime.
        In that case, delete the test, it is only useful until the time the DB migration has not run.
        It should be safe to assume after one deployment the DB migration would have run through
        and will become outdated eventually"""

        library = self.create_library()
        self._associate_us_states(library, ["NY", "HI"])
        country_library = self.create_library(allow_all_us_states=True)
        migration = import_module(
            "virtuallibrarycard.migrations.0074_auto_20221018_0809"
        )
        migration.migrate_states_to_places(apps, None)

        places = list(library.library_places.all())
        assert len(places) == 2
        assert ["Hawaii", "New York"] == sorted(map(lambda p: p.place.name, places))

        # Allow all states should associate to the country
        places = list(country_library.library_places.all())
        # The create_library testing code always adds new york
        assert ["New York", "United States"] == sorted(
            map(lambda p: p.place.name, places)
        )

        # A non-existent state should fail
        bad_state_library = self.create_library(places=[])
        self._associate_us_states(bad_state_library, ["ZZ"])
        with pytest.raises(RuntimeError):
            migration.migrate_states_to_places(apps, None)

    def test_user_migration(self):
        user = self.create_user(self._default_library)
        user.us_state = "AL"
        user.save()

        assert user.place.abbreviation == "NY"

        migration = import_module(
            "virtuallibrarycard.migrations.0076_auto_20221019_1011"
        )
        migration.migrate_user_state_to_place(apps, None)

        user.refresh_from_db()
        # Place changed to us_state
        assert user.place.abbreviation == "AL"

        # Bad state name
        user.us_state = "ZZ"
        user.save()

        migration.migrate_user_state_to_place(apps, None)

        # Does not change, but did not throw an error either
        assert user.place.abbreviation == "AL"
