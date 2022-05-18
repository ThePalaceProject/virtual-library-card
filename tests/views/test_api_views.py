from datetime import datetime, timedelta

from django.core.handlers.wsgi import WSGIRequest
from django.test import RequestFactory

from tests.base import BaseUnitTest
from VirtualLibraryCard.models import CustomUser, LibraryCard
from VirtualLibraryCard.views.views_api import PinTestViewSet, UserLibraryCardViewSet


class TestPinTestViewSet(BaseUnitTest):
    def _setup_view(
        self, card: LibraryCard, user: CustomUser, password: str
    ) -> PinTestViewSet:
        user.set_password(password)
        user.save()
        request: WSGIRequest = RequestFactory().get(
            f"/{card.number}/{password}/pintest"
        )
        view = PinTestViewSet()
        view.setup(request)
        return view

    def test_get_method(self):
        password = "apassword"
        view = self._setup_view(self._default_card, self._default_user, password)
        response = view.get(view.request, self._default_card.number, password)

        assert response.data["RETCOD"] == 0

    def test_bad_pin(self):
        password = "apassword"
        view = self._setup_view(self._default_card, self._default_user, password)
        response = view.get(view.request, self._default_card.number, password + "NOT")

        assert response.data["RETCOD"] == 1
        assert response.data["ERRNUM"] == 4
        assert response.data["ERRMSG"] == "Invalid patron PIN"

    def test_bad_card(self):
        password = "apassword"
        view = self._setup_view(self._default_card, self._default_user, password)
        response = view.get(view.request, self._default_card.number + "xx", password)

        assert response.data["RETCOD"] == 1
        assert response.data["ERRNUM"] == 1
        assert response.data["ERRMSG"] == "Requested record not found"

    def test_api(self):
        password = "apassword"
        self._default_user.set_password(password)
        self._default_user.save()
        card = self._default_card

        response = self.client.get(f"/api/{card.number}/{password}/pintest")
        assert response.content == b"<HTML>\n<BODY>\nRETCOD=0<BR>\n</BODY>\n</HTML>"

        response = self.client.get(f"/PATRONAPI/{card.number}/{password}/pintest")
        assert response.content == b"<HTML>\n<BODY>\nRETCOD=0<BR>\n</BODY>\n</HTML>"


class TestUserLibraryCardViewSet(BaseUnitTest):
    def _setup_view(self, card: LibraryCard) -> UserLibraryCardViewSet:
        request: WSGIRequest = RequestFactory().get(f"/{card.number}/dump")
        view = UserLibraryCardViewSet()
        view.setup(request)
        return view

    def test_get(self):
        view = self._setup_view(self._default_card)
        response = view.get(view.request, self._default_card.number)

        assert "library_cards" in response.data
        assert len(response.data["library_cards"]) == 1
        data = response.data["library_cards"][0]
        assert data == self._default_card

    def test_bad_number(self):
        view = self._setup_view(self._default_card)
        response = view.get(view.request, self._default_card.number + "xx")

        assert response.data["ERRNUM"] == 1
        assert response.data["ERRMSG"] == "Requested record not found"

    def test_api(self):
        card = self.create_library_card(
            self._default_user,
            self._default_library,
            expiration_date=datetime.today() + timedelta(days=1),
        )

        expected = (
            f"<HTML>\n<BODY>\n"
            f"EXP DATE[p43]={card.expiration_date.strftime('%m-%d-%y')}<BR>\n"
            f"HOME LIBR[p53]={card.library.identifier}<BR>"
            f"\nCREATED[p83]={card.created.strftime('%m-%d-%y')}<BR>"
            f"\nPATRN NAME[pn]={card.user.get_smart_name()}<BR>"
            f"\nADDRESS[pa]={card.user.street_address_line1}<BR>\n"
            f"P BARCODE[pb]={card.number}<BR>\n</BODY>\n</HTML>"
        )

        response = self.client.get(f"/PATRONAPI/{card.number}/dump")
        assert response.content == expected.encode()

        response = self.client.get(f"/api/{card.number}/dump")
        assert response.content == expected.encode()
