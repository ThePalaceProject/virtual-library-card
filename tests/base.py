import sys
from logging import StreamHandler
from random import choice
from unittest import mock

import pytest
from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.db import transaction
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from virtual_library_card.logging import log
from virtuallibrarycard.models import (
    CustomUser,
    Library,
    LibraryCard,
    LibraryPlace,
    Place,
)

log.removeHandler(log.handlers[0])
log.addHandler(StreamHandler(stream=sys.stdout))


class TestData:
    LOWER_ALPH = [chr(i) for i in range(ord("a"), ord("z") + 1)]
    UPPER_ALPH = [chr(i) for i in range(ord("A"), ord("Z") + 1)]
    NUM = [chr(i) for i in range(ord("0"), ord("9") + 1)]
    VALID_CHARS = LOWER_ALPH + UPPER_ALPH + NUM

    def _random_name(self, length=8):
        return "".join([choice(self.VALID_CHARS) for i in range(length)])

    def seed_data(self):
        self._default_library = self.create_library(
            name="Default", identifier="default", prefix="00df"
        )
        self._default_user = self.create_user(
            self._default_library,
            email="default@example.com",
            password="xxx",
            first_name="Default",
        )
        self._default_card = self.create_library_card(
            self._default_user, self._default_library
        )

    def create_library(
        self,
        name=None,
        identifier=None,
        places=None,
        prefix=None,
        bulk_upload_prefix=None,
        **kwargs,
    ):
        obj = Library(
            name=name or self._random_name(),
            identifier=identifier or self._random_name(),
            prefix=prefix or self._random_name(),
            bulk_upload_prefix=bulk_upload_prefix or self._random_name(),
            logo=kwargs.pop("logo", "http://example.logo/"),
            phone=kwargs.pop("phone", "999999999"),
            email=kwargs.pop("email", "default@example.com"),
            terms_conditions_url=kwargs.pop(
                "terms_condition_url", "http://example.terms/"
            ),
            privacy_url=kwargs.pop("privacy_url", "http://example.privacy/"),
            **kwargs,
        )
        obj.save()

        for s in places if places is not None else ["NY"]:
            LibraryPlace.associate(obj, s)
        obj.save()

        return obj

    def create_user(
        self,
        library,
        email=None,
        password=None,
        first_name=None,
        place_abbreviation="NY",
        **kwargs,
    ):
        user = CustomUser(
            email=email or f"{self._random_name()}@example.com",
            password=password or self._random_name(),
            library=library,
            first_name=first_name or self._random_name(),
            **kwargs,
        )
        user.place = Place.by_abbreviation(place_abbreviation)
        user.save()
        return user

    def create_library_card(self, user, library, **kwargs):
        card = LibraryCard(user=user, library=library, **kwargs)
        card.save()
        return card


@pytest.mark.django_db
class BaseUnitTest(TestData, TestCase):
    def setup_method(self, request):
        # Fake a transaction block
        self._transaction = transaction.atomic()
        self._transaction.__enter__()

        # seed the data
        self.seed_data()

    def tearDown(self):
        # Needs to be the django tearDown and not pytest teardown_method
        # Rollback any DB changes made this test
        transaction.set_rollback(True)
        self._transaction.__exit__(None, None, None)
        super().tearDown()

    def do_library_card_signup_flow(self, client: Client, library: Library = None):
        """A common flow which is needed multiple times"""

        if not library:
            library = self._default_library

        with mock.patch(
            "virtuallibrarycard.views.views_library_card.Geolocalize"
        ) as mock_geolocalize:
            mock_geolocalize.get_user_location.return_value = {
                "results": [
                    {
                        "locations": [
                            {
                                "adminArea1": "US",
                                "adminArea3": self._default_library.get_first_place(),
                                "adminArea5": "city",
                                "postalCode": "998867",
                            }
                        ]
                    }
                ]
            }
            resp = client.post(
                f"/account/library_card_signup/{library.identifier}/",
                dict(lat=10, long=10, identifier=library.identifier),
            )
            assert resp.status_code == 302

        return resp


class BaseAdminUnitTest(BaseUnitTest):
    MODEL = NotImplemented
    MODEL_ADMIN = NotImplemented

    def setup_method(self, request):
        ret = super().setup_method(request)
        # Use self.admin when testing single functions
        # With the mock request
        self.site = AdminSite()
        self.admin: ModelAdmin = self.MODEL_ADMIN(self.MODEL, self.site)
        self.mock_request = RequestFactory().get("/admin")
        self.super_user = CustomUser.objects.create_superuser(
            "test@admin.com", "password"
        )

        # Super user based client
        self.test_client = Client()
        self.test_client.force_login(self.super_user)

        return ret

    def get_change_url(self, obj):
        return reverse(
            f"admin:virtuallibrarycard_{self.MODEL.__name__.lower()}_change",
            kwargs={"object_id": obj.id},
        )

    def get_add_url(self):
        return reverse(f"admin:virtuallibrarycard_{self.MODEL.__name__.lower()}_add")

    def _response_errors(self, response):
        """Helper function for debuging form submits"""
        return response.context[0]["adminform"].errors


class MockThread:
    """Mock threading for test runs"""

    def __init__(self, target=None, args=None, kwargs=None, daemon=True):
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.daemon = daemon

    def start(self):
        """synchronous run"""
        args = self.args or []
        kwargs = self.kwargs or {}
        self.target(*args, **kwargs)
