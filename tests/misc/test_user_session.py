from datetime import datetime
from unittest import mock

from datedelta import datedelta

from tests.base import BaseUnitTest
from virtual_library_card.user_session import UserSessionManager


class TestUserSessionManager(BaseUnitTest):
    def test_set_request_session_library(self):
        library = self.create_library(
            social_facebook="fb",
            social_twitter="tw",
            places=["NY"],
        )
        request = mock.MagicMock()
        request.session = dict()
        UserSessionManager.set_request_session_library(request, library)
        assert request.session["library_phone"] == library.phone
        assert request.session["identifier"] == library.identifier
        assert request.session["library_name"] == library.name
        assert request.session["social_facebook"] == library.social_facebook
        assert request.session["social_twitter"] == library.social_twitter
        assert request.session["email"] == library.email
        assert request.session["places"] == ["NY"]
        assert request.session["terms_conditions_url"] == library.terms_conditions_url
        assert request.session["privacy_url"] == library.terms_conditions_url

    def test_clean_session_data(self):
        request = mock.MagicMock()
        UserSessionManager.clean_session_data(request)
        request.session.pop.assert_has_calls(
            [
                mock.call("sess_variable", None),
                mock.call("library_phone", None),
                mock.call("identifier", None),
                mock.call("library_name", None),
                mock.call("social_facebook", None),
                mock.call("social_twitter", None),
                mock.call("logo_header", None),
                mock.call("email", None),
                mock.call("places", None),
                mock.call("terms_conditions_url", None),
            ]
        )

    def test_set_context_library_cards(self):
        user = self.create_user(self._default_library)
        card = self.create_library_card(user, self._default_library)

        expired_card = self.create_library_card(user, self._default_library)
        expired_card.expiration_date = datetime.today() - datedelta(days=1)
        expired_card.save()

        future_card = self.create_library_card(user, self._default_library)
        future_card.expiration_date = datetime.today() + datedelta(days=1)
        future_card.save()

        context = {}
        UserSessionManager.set_context_library_cards(context, user)

        assert set(context["library_cards"]) == {card, future_card}
        assert context["nb_library_cards"] == 2

    def test_set_session_info(self):
        arg = mock.MagicMock()
        arg.request.session = {}
        arg.request.GET = {"identifier": self._default_library.identifier}
        result = UserSessionManager.set_session_info(arg)

        assert result == self._default_library.identifier
        assert len(arg.request.session.keys()) == 10

        arg.request.session = {}
        arg.request.GET = {"identifier": "someidentifier"}
        result = UserSessionManager.set_session_info(arg)

        assert result == "someidentifier"
        assert arg.request.session == {}

    def test_set_session_identifier_info(self):
        arg = mock.MagicMock()
        arg.request.session = {}
        UserSessionManager.set_session_identifier_info(
            arg, self._default_library.identifier
        )
        assert len(arg.request.session.keys()) == 10
        assert arg.request.session["identifier"] == self._default_library.identifier

        # Alternative identifier within request
        arg.request.session = {}
        arg.request.GET = {"identifier": self._default_library.identifier}
        UserSessionManager.set_session_identifier_info(arg, None)
        assert len(arg.request.session.keys()) == 10
        assert arg.request.session["identifier"] == self._default_library.identifier

        # No identifiers
        arg.request.session = {}
        arg.request.GET = {"identifier": None}
        UserSessionManager.set_session_identifier_info(arg, None)
        assert len(arg.request.session.keys()) == 0

        # Bad identifier does not fallback to alternative (silent failure!)
        arg.request.session = {}
        arg.request.GET = {"identifier": self._default_library.identifier}
        UserSessionManager.set_session_identifier_info(arg, "badidentifier")
        assert len(arg.request.session.keys()) == 0
