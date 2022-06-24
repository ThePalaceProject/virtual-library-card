from django.core.management.commands.makemigrations import Command  # noqa
from django.db import models
from localflavor.us.models import USPostalCodeField, USStateField

# Ignore decorative attributes from creeping into migrations
IGNORED_ATTRS = ["verbose_name", "help_text", "choices"]

original_deconstruct = models.Field.deconstruct


def new_deconstruct(self):
    name, path, args, kwargs = original_deconstruct(self)
    for attr in IGNORED_ATTRS:
        # These 2 fields delete choices themselves
        if attr == "choices" and type(self) in (USStateField, USPostalCodeField):
            continue

        kwargs.pop(attr, None)
    return name, path, args, kwargs


models.Field.deconstruct = new_deconstruct
