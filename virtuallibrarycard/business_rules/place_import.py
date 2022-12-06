"""Only use this file for the place import logic from files

IMPORTANT: DO NOT IMPORT THE Place MODEL INTO THIS FILE

It is used in the migration code and will break if we import actual
models during the migrate step"""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
    from virtuallibrarycard.models import Place

if "Place" in locals():
    raise RuntimeError("DO NOT IMPORT THE Place MODEL INTO THIS FILE")


@dataclass
class PlaceObject:
    # This is not a DB id, it is simply a marker that allows the ndjson items to refer to each other
    id: str
    name: str
    type: str
    abbreviation: str = ""
    latitude: float = None
    longitude: float = None
    # This is not a DB id, this should refer to any ndjson id that exists prior in the file
    parent_id: str = None

    def __post_init__(self):
        # ensure external id types
        self.id = str(self.id)
        if self.parent_id is not None:
            self.parent_id = str(self.parent_id)

    def model_json(self):
        """Export the PlaceObject as a json conforming the Place DB model"""
        return dict(
            external_id=self.id,
            name=self.name,
            type=self.type,
            abbreviation=self.abbreviation,
            longitude=self.longitude,
            latitude=self.latitude,
        )


class PlaceImport:
    def __init__(self, place_model: Place):
        self.place_model = place_model

    def import_ndjson(self, io: IO):
        """Import Place model data from an ndjson file
        The json lines should have the format as specified in the `PlaceObject` class
        Any refrenced parent_id must always be present before the row that refrences it
        Eg. sample_places.ndjson"""
        # We depend on the order of presented places
        imported = OrderedDict()
        places = {}
        for line in io.readlines():
            data = json.loads(line)
            obj = PlaceObject(**data)
            _id = obj.id
            imported[_id] = obj

            if obj.parent_id:
                if obj.parent_id not in places:
                    raise PlaceImportParentOrderException(
                        f"The parent_id {obj.parent_id} must be present in an earlier line than {line}"
                    )
                parent = places[obj.parent_id]
            else:
                parent = None

            place = self.place_model.objects.filter(external_id=_id).first()
            if not place:
                # Create a new place
                place = self.place_model(parent=parent, **obj.model_json())
            else:
                # Update all attributes, this removes missing attributes
                for key, val in obj.model_json().items():
                    setattr(place, key, val)
                place.parent = parent

            places[_id] = place
            place.save()


class PlaceImportParentOrderException(Exception):
    pass
