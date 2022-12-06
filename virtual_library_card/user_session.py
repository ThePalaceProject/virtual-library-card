from datetime import datetime

from virtual_library_card.logging import log
from virtuallibrarycard.models import Library, LibraryCard


class UserSessionManager:
    @staticmethod
    def set_session_identifier_info(self, identifier):
        if identifier:
            try:
                library = Library.objects.filter(identifier=identifier).first()
                UserSessionManager.set_session_library(self, library)
            except Exception as e:
                log.error(f"Set session identifier error {e}")
            return identifier
        else:
            return UserSessionManager.set_session_info(self)

    @staticmethod
    def set_session_info(self):
        identifier = self.request.GET.get("identifier", None)
        if identifier:
            try:
                library = Library.objects.filter(identifier=identifier).first()
                UserSessionManager.set_session_library(self, library)
            except Exception as e:
                log.error(f"Set session info error {e}")
        return identifier

    @staticmethod
    def set_session_user_location(request, state, city, zipcode):
        request.session["state"] = state
        request.session["city"] = city
        request.session["zipcode"] = zipcode

    @staticmethod
    def set_session_library(self, library):
        UserSessionManager.set_request_session_library(self.request, library)

    @staticmethod
    def set_request_session_library(request, library):
        request.session["library_phone"] = library.phone
        request.session["identifier"] = library.identifier
        request.session["library_name"] = library.name
        request.session["social_facebook"] = library.social_facebook
        request.session["social_twitter"] = library.social_twitter
        request.session["logo_header"] = library.logo_header()
        request.session["email"] = library.email
        request.session["places"] = library.get_places()
        request.session["terms_conditions_url"] = library.terms_conditions_url
        request.session["privacy_url"] = library.terms_conditions_url

    @staticmethod
    def clean_session_data(request):
        request.session.pop("sess_variable", None)
        request.session.pop("library_phone", None)
        request.session.pop("identifier", None)
        request.session.pop("library_name", None)
        request.session.pop("social_facebook", None)
        request.session.pop("social_twitter", None)
        request.session.pop("logo_header", None)
        request.session.pop("email", None)
        request.session.pop("places", None)
        request.session.pop("terms_conditions_url", None)
        # Also cleanup user location data
        request.session.pop("state", None)
        request.session.pop("city", None)
        request.session.pop("zipcode", None)

    @staticmethod
    def set_context_library_cards(context, user):
        """
        :param context:
        """
        now = datetime.today()
        library_cards = LibraryCard.objects.filter(
            user=user, canceled_date=None
        ).exclude(expiration_date__lte=now)
        context["library_cards"] = library_cards
        context["nb_library_cards"] = library_cards.count()
