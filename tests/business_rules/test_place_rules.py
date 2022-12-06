import json
from io import StringIO

import pytest

from tests.base import BaseUnitTest
from virtuallibrarycard.business_rules.place_import import (
    PlaceImport,
    PlaceImportParentOrderException,
)
from virtuallibrarycard.models import Place


class TestPlaceImport(BaseUnitTest):
    def test_import_ndjson(self):
        prev_count = Place.objects.count()

        with open("tests/files/sample_places.ndjson") as fp:
            PlaceImport(Place).import_ndjson(fp)

        assert Place.objects.count() - prev_count == 3

        usa = Place.objects.get(external_id="1")
        assert usa.parent == None
        assert usa.type == Place.Types.COUNTRY
        assert usa.abbreviation == "US"
        assert usa.longitude == 10
        assert usa.latitude == 10.00000000000004

        iowa = Place.objects.get(external_id="101")
        assert iowa.parent == usa
        assert iowa.type == Place.Types.STATE
        assert iowa.longitude == None

        des_moines = Place.objects.get(external_id="des moines")
        assert des_moines.parent == iowa
        assert des_moines.type == Place.Types.CITY

    def test_import_ndjson_update(self):
        prev_count = Place.objects.count()
        with open("tests/files/sample_places.ndjson") as fp:
            PlaceImport(Place).import_ndjson(fp)

        assert Place.objects.count() - prev_count == 3

        # Read the DB before the update, so we know the objects have been updated and not created
        usa = Place.objects.get(external_id="1")
        des_moines = Place.objects.get(external_id="des moines")

        update = json.dumps(dict(id="1", name="United States", type="country")) + "\n"
        update += json.dumps(
            dict(
                id="des moines",
                name="Des Moines City",
                abbreviation="DMC",
                latitude=11,
                parent_id=1,
                type="county",
            )
        )

        PlaceImport(Place).import_ndjson(StringIO(update))

        usa.refresh_from_db()
        des_moines.refresh_from_db()
        assert usa.abbreviation == ""  # missing data WAS deleted
        assert des_moines.name == "Des Moines City"
        assert des_moines.type == Place.Types.COUNTY
        assert des_moines.latitude == 11
        assert des_moines.abbreviation == "DMC"
        assert des_moines.parent == usa

    def test_import_ndjson_order_error(self):
        update = (
            json.dumps(dict(id="1", name="United States", type="country", parent_id=0))
            + "\n"
        )
        update += json.dumps(dict(id=0, name="earth", type="planet"))

        # Out of order parent links will raise an error
        with pytest.raises(PlaceImportParentOrderException):
            PlaceImport(Place).import_ndjson(StringIO(update))
