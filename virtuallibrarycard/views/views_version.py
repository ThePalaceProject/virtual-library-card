from rest_framework import permissions
from rest_framework.decorators import permission_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

import virtual_library_card


@permission_classes((permissions.AllowAny,))
class VersionView(APIView):
    renderer_classes = [JSONRenderer]

    @staticmethod
    def get(request):
        return Response(
            {
                "version": virtual_library_card.__version__,
                "commit": virtual_library_card.__commit__,
                "branch": virtual_library_card.__branch__,
            },
            content_type="application/json",
        )
