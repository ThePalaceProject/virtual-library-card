from django.http import Http404

from VirtualLibraryCard.models import *

from .views import *
from .views_api import *
from .views_library_card import *
from .views_password import *
from .views_profile import *


def debug_templates(request, template_path=None):
    """DEBUG ONLY: Template testing.
    Using this view any template in the django templates directories can be tested
    using GET parameters to fill in any context variables for the templates"""
    # Only superusers can access this URL, even on development envs
    if not request.user.is_superuser:
        raise Http404()

    context = {}
    for k, v in request.GET.items():
        context[k] = request.GET.get(k)

    # In case the template contexts need DB objects
    # we can provide the data in a string format, which will be converted to the object
    # Generic format: __id__{model name}__{template var name} = {object id in DB}
    # Eg. If the template needs a Library object and we would like to test via Library(id=22)
    # then we provide the GET parameter __id__Library__library=22
    # Which translates to __id__ prefix, DB table = Library with id=22, template variable = library
    id_prefix = "__id__"
    model_context = {}
    for key, value in context.items():
        if key.startswith(id_prefix):
            parts = key.split("__")
            model_name = parts[2]
            key_name = parts[3]
            model = globals().get(model_name)
            obj = model.objects.get(id=int(value))
            model_context[key_name] = obj

    context.update(model_context)
    return render(request, template_path, context)
