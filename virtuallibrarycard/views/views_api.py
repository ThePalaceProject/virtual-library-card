from dal import autocomplete
from django.contrib.auth import authenticate
from django.utils.translation import gettext as _
from rest_framework import permissions
from rest_framework.decorators import permission_classes
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from virtual_library_card.geoloc import Geolocalize
from virtual_library_card.logging import LoggingMixin
from virtuallibrarycard.models import CustomUser, LibraryCard, Place


@permission_classes((permissions.AllowAny,))
class PinTestViewSet(LoggingMixin, APIView):
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "api/pin_test.html"

    @staticmethod
    def execute(log, number, pin):
        library_card: LibraryCard = LibraryCard.objects.filter(number=number).first()
        if library_card:

            user: CustomUser = library_card.user
            authenticated_user = authenticate(email=user.email, password=pin)
            log.debug(f"authenticated_user {authenticated_user}")
            if authenticated_user:
                if not user.email_verified:
                    return Response(
                        {
                            "RETCOD": 1,
                            "ERRNUM": 5,
                            "ERRMSG": _("Patron has an unverified email address"),
                        }
                    )
                return Response({"RETCOD": 0})
            else:
                return Response(
                    {"RETCOD": 1, "ERRNUM": 4, "ERRMSG": _("Invalid patron PIN")}
                )

        else:
            return Response(
                {"RETCOD": 1, "ERRNUM": 1, "ERRMSG": _("Requested record not found")}
            )

    # / PATRONAPI / {barcode} / {pin} / pintest
    def get(self, request, number, pin):
        return PinTestViewSet.execute(self.log, number, pin)


@permission_classes((permissions.AllowAny,))
class PinTestPOSTViewSet(LoggingMixin, APIView):
    """A separate controller for handling POST requests."""

    renderer_classes = [TemplateHTMLRenderer]
    template_name = "api/pin_test.html"

    def post(self, request):
        if "number" in request.data and "pin" in request.data:
            number = request.data["number"]
            pin = request.data["pin"]
            return PinTestViewSet.execute(self.log, number, pin)
        else:
            return Response(
                {
                    "RETCOD": 1,
                    "ERRNUM": 100000,
                    "ERRMSG": _("Missing required parameter(s): 'number' and 'pin'"),
                }
            )


@permission_classes((permissions.AllowAny,))
class UserLibraryCardViewSet(APIView):
    # serializer_class = LibraryCardSerializer
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "api/dump.html"

    # / PATRONAPI / {barcode} / dump
    # def list(self, request, *args, **kwargs):
    #     return super().list(request, *args, **kwargs)

    def get(self, request, number):
        library_cards = LibraryCard.objects.filter(number=number)
        if library_cards:
            return Response({"library_cards": library_cards})
        return Response({"ERRNUM": 1, "ERRMSG": _("Requested record not found")})


@permission_classes((permissions.IsAdminUser,))
class PlaceSearchAheadView(autocomplete.Select2ListView, APIView):
    def get_list(self):
        query = self.q

        if not query:
            return []

        if len(query) < 2 or len(query) > 100:
            return []

        content, status = Geolocalize.search_for_places(query)

        if status == 200:
            content = PlaceSearchAheadView.extract_places_to_list(content)

        return content

    @staticmethod
    def extract_places_to_list(api_response):
        place_types = {
            Place.Types.COUNTRY,
            Place.Types.STATE,
            Place.Types.PROVINCE,
            Place.Types.COUNTY,
            Place.Types.CITY,
        }

        results = []
        for record in api_response["results"]:
            record_type = record["recordType"]

            if record_type not in place_types:
                continue

            if (
                record_type == "state"
                and record["place"]["properties"]["country"] == "Canada"
            ):
                record_type = Place.Types.PROVINCE

            # For the id we are using place name and API's id so it is unique, because it is needed for the select2
            # library. In the form we are sending only the place name back to the backend to be saved.
            place_record = {
                "id": f"{record['name']}|{record['id']}",
                "name": record["name"],
                "text": f"{record['displayString']} | {record_type}",
                "type": record["recordType"],
            }

            place_record["parents"] = PlaceSearchAheadView.create_parents_list(
                record["place"]["properties"]
            )

            results.append(place_record)

        return results

    @staticmethod
    def create_parents_list(place_properties):
        # We are creating list of parents received by the API were first we have most immediate parents, i.e. for city
        # we have [county, state, country].
        parent_place_types = [
            Place.Types.COUNTRY,
            Place.Types.STATE,
            Place.Types.COUNTY,
        ]

        parents = []
        for parent_type in parent_place_types:
            if place_properties["type"] == parent_type:
                return parents

            if parent_type in place_properties:
                parent = PlaceSearchAheadView._extract_parent(
                    place_properties, parent_type
                )

                if (
                    parent["type"] == "state"
                    and place_properties["country"] == "Canada"
                ):
                    parent["type"] = "province"

                parents.append(parent)

        return list(reversed(parents))

    @staticmethod
    def _extract_parent(place_properties, place_type):
        obj = {"type": place_type, "value": place_properties[place_type]}

        return obj

    def autocomplete_results(self, results):
        """Overridden parent method to support multiple attributes"""
        if all(isinstance(el, dict) for el in results) and len(results) > 0:
            return results

        return super().autocomplete_results(results)

    def results(self, results):
        """Overridden parent method to support multiple attributes"""
        if all(isinstance(el, dict) for el in results) and len(results) > 0:
            return results

        return super().results(results)

    def create(self, text):
        """Adds the ability to input places not found in the Mapquest API."""
        return text
