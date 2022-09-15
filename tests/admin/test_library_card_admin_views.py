from tests.base import BaseAdminUnitTest
from VirtualLibraryCard.admin import LibraryCardAdmin
from VirtualLibraryCard.models import LibraryCard


class TestLibraryAdminViews(BaseAdminUnitTest):
    MODEL = LibraryCard
    MODEL_ADMIN = LibraryCardAdmin

    def _get_card_data(self, card: LibraryCard = None, **data):
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
        self.assertFormError(
            response,
            "adminform",
            "number",
            ["This number already exists for this library"],
        )
