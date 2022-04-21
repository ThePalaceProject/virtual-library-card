from random import choice
from unittest import mock

import pytest
from django.db import transaction
from django.test import Client

from VirtualLibraryCard.models import CustomUser, Library, LibraryCard, LibraryStates


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

    def create_library(self, name=None, identifier=None, us_states=None, **kwargs):
        obj = Library(
            name=name or self._random_name(),
            identifier=identifier or self._random_name(),
            logo=kwargs.get("logo", "http://example.logo/"),
            phone=kwargs.get("phone", "999999999"),
            email=kwargs.get("email", "default@example.com"),
            terms_conditions_url=kwargs.get(
                "terms_condition_url", "http://example.terms/"
            ),
            privacy_url=kwargs.get("privacy_url", "http://example.privacy/"),
            **kwargs,
        )
        obj.save()

        library_states = [
            LibraryStates(us_state=s, library=obj) for s in (us_states or ["NY"])
        ]
        for ls in library_states:
            ls.save()
        obj.library_states.set(library_states)
        obj.save()

        return obj

    def create_user(
        self,
        library,
        email=None,
        password=None,
        first_name=None,
        us_state="NY",
        **kwargs,
    ):
        user = CustomUser(
            email=email or f"{self._random_name()}@example.com",
            password=password or self._random_name(),
            library=library,
            us_state=us_state,
            first_name=first_name or self._random_name(),
            **kwargs,
        )
        user.save()
        return user

    def create_library_card(self, user, library):
        card = LibraryCard(user=user, library=library)
        card.save()
        return card


@pytest.mark.django_db
class BaseUnitTest(TestData):
    def setup_method(self, request):
        # Fake a transaction block
        self._transaction = transaction.atomic()
        self._transaction.__enter__()

        # seed the data
        self.seed_data()

    def teardown_method(self, request):
        # Rollback any DB changes made this test
        transaction.set_rollback(True)
        self._transaction.__exit__(None, None, None)

    def do_library_card_signup_flow(self, client: Client):
        """A common flow which is needed multiple times"""
        with mock.patch(
            "VirtualLibraryCard.views.views_library_card.Geolocalize"
        ) as mock_geolocalize:
            mock_geolocalize.get_user_location.return_value = {
                "results": [
                    {
                        "locations": [
                            {
                                "adminArea1": "US",
                                "adminArea3": self._default_library.get_first_us_state(),
                                "adminArea5": "city",
                                "postalCode": "998867",
                            }
                        ]
                    }
                ]
            }
            resp = client.post(
                f"/account/library_card_signup/{self._default_library.identifier}/",
                dict(lat=10, long=10, identifier=self._default_library.identifier),
            )
            assert resp.status_code == 302

        return resp
