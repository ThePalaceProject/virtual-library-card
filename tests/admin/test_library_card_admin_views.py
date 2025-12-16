from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from pytest_django.asserts import assertFormError

from tests.base import BaseAdminUnitTest, BaseUnitTest
from virtuallibrarycard.admin import LibraryCardAdmin, LibraryCardsUploadCSV
from virtuallibrarycard.forms.forms import LibraryCardsUploadByCSVForm
from virtuallibrarycard.models import LibraryCard


class TestLibraryCardAdminViews(BaseAdminUnitTest):
    MODEL = LibraryCard
    MODEL_ADMIN = LibraryCardAdmin

    def _get_card_data(self, card: LibraryCard | None = None, **data):
        initial = {
            "number": "",
            "created": "",
            "expiration_date": "",
            "library": "",
            "user": "",
            "canceled_date": "",
            "canceled_by_user": "",
        }

        if card is not None:
            for k, v in initial.items():
                initial[k] = getattr(card, k)

        for k, v in data.items():
            initial[k] = v

        return initial

    def test_create_card_with_number(self):
        user = self.create_user(self._default_library)
        data = self._get_card_data(
            number="0001",
            library=self._default_library.id,
            user=user.id,
        )

        response = self.test_client.post(self.get_add_url(), data)
        cards = LibraryCard.objects.filter(user=user)

        assert response.status_code == 302
        assert len(cards) == 1
        assert cards[0].number == f"{self._default_library.prefix}0001"

    def test_create_card_no_number(self):
        user = self.create_user(self._default_library)
        data = self._get_card_data(
            library=self._default_library.id,
            user=user.id,
        )
        response = self.test_client.post(self.get_add_url(), data)
        cards = LibraryCard.objects.filter(user=user)
        prefix = self._default_library.prefix

        assert response.status_code == 302
        assert len(cards) == 1
        assert cards[0].number != None
        assert cards[0].number.startswith(prefix)
        assert cards[0].number != prefix  # we are not only the prefix, but more

    def test_create_card_with_number_not_unique(self):
        prefix = self._default_library.prefix
        user = self.create_user(self._default_library)

        card = self.create_library_card(
            self._default_user, self._default_library, number=f"{prefix}001"
        )
        assert card.number == f"{prefix}001"

        data = self._get_card_data(
            library=self._default_library.id, user=user.id, number="001"
        )
        response = self.test_client.post(self.get_add_url(), data)
        cards = LibraryCard.objects.filter(user=user)

        assert response.status_code == 200
        assert len(cards) == 0
        assertFormError(response.context['adminform'],
            "number",
            ["This number already exists for this library"],
        )

    @patch("virtuallibrarycard.admin.admin.ModelAdmin.change_view")
    def test_change_view(self, mock_super):
        # A card with a user gets a reset url for the template context
        self.admin.change_view(None, str(self._default_card.id), "", dict())
        assert mock_super.call_count == 1
        assert mock_super.call_args_list[0][0][3] == dict(
            reset_password_url=f"../../../customuser/{self._default_card.user.id}/password"
        )

        # Card without a user has no reset url
        mock_super.reset_mock()
        card = self.create_library_card(self._default_user, self._default_library)
        card.user = None
        card.save()
        self.admin.change_view(None, str(card.id), "", dict())
        assert mock_super.call_args_list[0][0][3] == dict()


class TestLibraryCardUploadsCSV(BaseUnitTest):
    def test_permissions(self):
        rf = RequestFactory()
        library = self.create_library()
        superuser = self.create_user(library, is_superuser=True)
        staff = self.create_user(library, is_staff=True)
        other_staff = self.create_user(self._default_library, is_staff=True)
        just_user = self.create_user(library)

        get = rf.get("/")
        post = rf.post("/", data={"library": library.id})

        view = LibraryCardsUploadCSV()

        view.setup(get)
        get.user = superuser
        assert view.dispatch(get).status_code == 200

        get.user = staff
        assert view.dispatch(get).status_code == 200

        get.user = just_user
        with pytest.raises(PermissionDenied):
            view.dispatch(get)

        view.setup(post)
        post.user = superuser
        assert view.dispatch(post).status_code == 200

        post.user = staff
        assert view.dispatch(post).status_code == 200

        # Other library staff may not modify this library
        post.user = other_staff
        with pytest.raises(PermissionDenied):
            assert view.dispatch(post).status_code == 200

        # nor can a user
        post.user = just_user
        with pytest.raises(PermissionDenied):
            assert view.dispatch(post).status_code == 200


class TestLibraryCardsUploadByCSVForm(BaseUnitTest):
    def test_library_field(self):
        library = self.create_library()
        superuser = self.create_user(library, is_superuser=True)
        staff = self.create_user(library, is_staff=True)

        library.allow_bulk_card_uploads = True
        self._default_library.allow_bulk_card_uploads = True
        self._default_library.save()
        library.save()

        form = LibraryCardsUploadByCSVForm(superuser)
        assert set(form.fields["library"].choices) == {
            (library.id, library.name),
            (self._default_library.id, self._default_library.name),
        }

        form = LibraryCardsUploadByCSVForm(staff)
        assert set(form.fields["library"].choices) == {
            (library.id, library.name),
        }
