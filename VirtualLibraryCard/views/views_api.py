from django.contrib.auth import authenticate
from django.utils.translation import gettext as _
from rest_framework import permissions
from rest_framework.decorators import permission_classes
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from virtual_library_card.logging import LoggingMixin
from VirtualLibraryCard.models import CustomUser, LibraryCard


@permission_classes((permissions.AllowAny,))
class PinTestViewSet(LoggingMixin, APIView):
    # serializer_class = LibraryCardSerializer
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "api/pin_test.html"

    # / PATRONAPI / {barcode} / {pin} / pintest
    def get(self, request, number, pin):
        library_card: LibraryCard = LibraryCard.objects.filter(number=number).first()
        if library_card:

            user: CustomUser = library_card.user
            authenticated_user = authenticate(email=user.email, password=pin)
            self.log.debug(f"authenticated_user {authenticated_user}")
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
