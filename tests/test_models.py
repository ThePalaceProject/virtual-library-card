import random
from datetime import datetime
from unittest.mock import MagicMock

import django
import pytest
from datedelta import datedelta
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from sequences import get_last_value

from tests.base import BaseUnitTest
from virtual_library_card.card_number import CardNumber
from VirtualLibraryCard.models import (
    CustomUser,
    Library,
    LibraryAllowedEmailDomains,
    LibraryCard,
)


class TestLibraryModel(BaseUnitTest):
    def test_create_default(self):
        library = Library.create_default_library()
        assert library.name == settings.DEFAULT_SUPERUSER_LIBRARY_NAME
        assert library.identifier == settings.DEFAULT_SUPERUSER_LIBRARY_IDENTIFIER
        assert library.prefix == settings.DEFAULT_SUPERUSER_LIBRARY_PREFIX
        assert library.get_us_states() == [settings.DEFAULT_SUPERUSER_LIBRARY_STATE]

    def test_generate_filename(self):
        filename = "testname.something.ext"
        generated = self._default_library.generate_filename(filename)
        assert (
            generated == f"uploads/library/logo_{self._default_library.identifier}.ext"
        )

    def test_get_us_states(self):
        us_states = ["AL", "TX", "WA", "KA"]
        library = self.create_library(us_states=us_states)
        assert library.get_us_states() == us_states

    def test_get_first_us_state(self):
        us_states = ["AL", "TX", "WA", "KA"]
        library = self.create_library(us_states=us_states)
        assert library.get_first_us_state() == "AL"

        # ensure this wasn't a fluke
        random.shuffle(us_states)
        l1 = self.create_library(us_states=us_states)
        l1.get_first_us_state() == us_states[0]

        random.shuffle(us_states)
        l2 = self.create_library(us_states=us_states)
        l2.get_first_us_state() == us_states[0]

    def test_get_logo_img(self):
        library = self._default_library
        filename = "testlogo.png"
        url = "http://example.com/"

        img_tag = library.get_logo_img(url, filename, False)
        assert (
            img_tag
            == f'<img  alt="{library.name} logo" aria-label="{library.name} logo"  src="{url}{filename}"  width="100px" />'
        )

        img_tag = library.get_logo_img(url, filename, True)
        assert (
            img_tag
            == f'<img  alt="{library.name} logo" aria-label="{library.name} logo"  src="{url}{filename}"  class="logo" />'
        )

    def test_logo_root_url(self):
        library = self.create_library(logo="somelogo")
        assert library.get_logo_root_url() == settings.MEDIA_URL

        library.logo = None
        assert library.get_logo_root_url() == settings.STATIC_URL + "images/"

    def test_logo_filename(self):
        library = self.create_library(logo="somelogo")
        assert library.logo_filename() == "somelogo"

        library.logo = None
        assert library.logo_filename() == "logo.png"

    def test_state_name(self):
        """library.state_name() is Not really used anywhere but still testing for it"""
        library = self.create_library(us_states=["NY"])
        assert library.state_name() == "New York"

    def test_allowed_domains(self):
        library = self.create_library()
        related = LibraryAllowedEmailDomains(library=library, domain="Example.org")
        related.save()
        related.refresh_from_db()

        # Domain is lowercased
        assert related.domain == "example.org"

        # Differently cased domain still trips the unique constraint
        with pytest.raises(
            django.db.utils.IntegrityError,
            match="duplicate key value violates unique constraint",
        ):
            with django.db.transaction.atomic():
                LibraryAllowedEmailDomains(library=library, domain="examPLE.org").save()

        # CustomUser unsavable in case of unmatched domain
        with pytest.raises(
            ValidationError,
            match="User must be part of allowed domains: \['example.org'\]",
        ):
            with django.db.transaction.atomic():
                CustomUser(library=library, email="email@notexample.org").save()

        # Same domain must work, case-insensitive
        CustomUser(library=library, email="email@EXample.org").save()
        assert CustomUser.objects.filter(email="email@EXample.org").count() == 1

    def test_save(self):
        # test the reset sequence is called
        prev_start_number = self._default_library.sequence_start_number
        last_value = get_last_value(
            CardNumber._card_number_sequence_name(self._default_library)
        )

        self._default_library.sequence_start_number += 20
        self._default_library.save()
        new_last_value = get_last_value(
            CardNumber._card_number_sequence_name(self._default_library)
        )

        assert last_value == prev_start_number
        assert new_last_value == prev_start_number + 20


class TestCustomUserModel(BaseUnitTest):
    def test_manager_create_user(self):
        user = CustomUser.objects.create_user(
            "email",
            "password",
            self._default_library,
            "NY",
            "first name",
            last_name="last name",
        )
        assert user.email == "email"
        assert user.us_state == "NY"
        assert user.first_name == "first name"
        assert user.library == self._default_library
        assert user.last_name == "last name"

    def test_manager_create_user_missing_fields(self):

        with pytest.raises(ValueError, match="The Email must be set"):
            CustomUser.objects.create_user(
                None,
                "password",
                self._default_library,
                "NY",
                "first name",
                last_name="last name",
            )

        with pytest.raises(ValueError, match="The Library must be set"):
            CustomUser.objects.create_user(
                "email",
                "password",
                None,
                "NY",
                "first name",
                last_name="last name",
            )

        with pytest.raises(ValueError, match="The State must be set"):
            CustomUser.objects.create_user(
                "email",
                "password",
                self._default_library,
                None,
                "first name",
                last_name="last name",
            )

        with pytest.raises(ValueError, match="The First name must be set"):
            CustomUser.objects.create_user(
                "email",
                "password",
                self._default_library,
                "NY",
                None,
                last_name="last name",
            )

    def test_manager_create_superuser(self):
        user = CustomUser.objects.create_superuser("email", "password")

        assert user.is_staff == True
        assert user.is_superuser == True
        assert user.is_active == True
        assert user.first_name == settings.DEFAULT_SUPERUSER_FIRST_NAME
        assert user.library.name == settings.DEFAULT_SUPERUSER_LIBRARY_NAME

    def test_manager_create_superuser_errors(self):
        with pytest.raises(ValueError, match="Superuser must have is_staff=True."):
            user = CustomUser.objects.create_superuser(
                "email", "password", is_staff=False
            )

        with pytest.raises(ValueError, match="Superuser must have is_superuser=True."):
            user = CustomUser.objects.create_superuser(
                "email", "password", is_superuser=False
            )

    def test_create_card_for_library(self):
        """Why is this method in CustomUser?"""
        user = self.create_user(self._default_library)
        card = CustomUser.create_card_for_library(user.library, user)
        assert card.user == user
        assert card.library == user.library
        assert card.expiration_date == None

    def test_get_smart_name(self):
        user = self.create_user(
            self._default_library,
            first_name=" spaced name",
            last_name="  more spacess   ",
        )
        assert user.get_smart_name() == "spaced name   more spacess"

        user.last_name = None
        assert user.get_smart_name() == "spaced name"

        user.first_name = None
        assert user.get_smart_name() == ""

        user.last_name = "name"
        assert user.get_smart_name() == "name"

    def test_library_states(self):
        assert self._default_user.library_states() == ["NY"]

    def test_get_library_state_name(self):
        assert self._default_user.library_state_name() == "New York"

    def test_group_permissions(self):
        group1 = Group.objects.create(name="Test Group 1")
        group2 = Group.objects.create(name="Test Group 2")
        self._default_user.groups.add(group1)
        self._default_user.groups.add(group2)
        assert self._default_user.groups_permission() == "Test Group 1,Test Group 2"

    def test_library_cards(self):
        user = self._default_user
        card1 = self._default_card
        card2 = self.create_library_card(user, self._default_library)
        card2.canceled_date = datetime.today()
        card2.save()
        lname = self._default_library.name

        expected = f"&mdash;&nbsp; {lname} | {card1.number}<br/>&mdash;&nbsp; {lname} | {card2.number} | CANCELLED"
        assert expected == user.library_cards()

    def test_nb_library_cards(self):
        user = self.create_user(self._default_library)
        assert user.nb_library_cards() == 0

        self.create_library_card(user, self._default_library)
        assert user.nb_library_cards() == 1

        self.create_library_card(user, self._default_library)
        assert user.nb_library_cards() == 2

    def test_library_admins(self):
        user = self.create_user(self._default_library, is_staff=True)
        assert list(CustomUser.library_admins(self._default_library).all()) == [user]

    def test_super_users(self):
        user = self.create_user(self._default_library, is_superuser=True)
        assert list(CustomUser.super_users().all()) == [user]

    def test_save(self):
        user = self.create_user(self._default_library)
        assert user.is_superuser == False
        assert user.is_staff == False

        user.is_superuser = True
        user.save()
        assert user.is_staff == True

    def test_get_or_create_default_library(self):
        """Why does this function exist in CustomUser?"""
        assert Library.objects.count() == 1

        default_library = CustomUser.get_or_create_default_library()
        assert Library.objects.count() == 2
        assert default_library.name == settings.DEFAULT_SUPERUSER_LIBRARY_NAME

        # Creates it only once
        default_library_again = CustomUser.get_or_create_default_library()
        assert Library.objects.count() == 2
        assert default_library == default_library_again


class TestLibraryCardModel(BaseUnitTest):
    def test_get_expiration_date(self):
        card = self.create_library_card(self._default_user, self._default_library)
        assert card.get_expiration_date() == None

        self._default_library.card_validity_months = 3
        self._default_library.save()
        assert card.get_expiration_date() is not None
        assert (
            card.get_expiration_date().date()
            == (datetime.today() + datedelta(months=3)).date()
        )

        # Validity does not change once set
        self._default_library.card_validity_months = 5
        self._default_library.save()
        assert card.library.card_validity_months == 5
        assert (
            card.get_expiration_date().date()
            == (datetime.today() + datedelta(months=3)).date()
        )

    def test_email(self):
        assert self._default_card.email() == self._default_user.email

    def test_str_dunder(self):
        card = self.create_library_card(self._default_user, self._default_library)
        assert str(card) == str(card.number)

        card1 = LibraryCard(library=self._default_library, user=self._default_user)
        assert str(card1) == f"{self._default_library.name} {self._default_user.email}"

    def test_save(self):
        card = LibraryCard()
        assert card.number == None

        # Save without library
        card.save()
        assert card.number is None

        card.library = self._default_library
        card.save()
        assert card.number is not None

    def test_is_expired(self):
        card = self._default_card
        assert card.is_expired() == False

        # Future date
        card.expiration_date = timezone.now() + datedelta(months=1)
        assert card.is_expired() == False

        # Past date
        card.expiration_date = timezone.now() - datedelta(months=1)
        assert card.is_expired() == True

    def test_status_str(self):
        card = self._default_card
        # default
        assert card.status_str() == ""

        # cancelled
        card.canceled_date = datetime.now()
        assert card.status_str() == " | CANCELLED"

        # expired
        card.canceled_date = None
        card.is_expired = MagicMock(return_value=True)
        assert card.status_str() == " | EXPIRED"
