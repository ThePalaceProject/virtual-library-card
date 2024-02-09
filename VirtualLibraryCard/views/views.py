from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils.translation import gettext
from django.views.generic.base import TemplateView


class Home(LoginRequiredMixin, TemplateView):
    template_name = "index.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context["message"] = gettext("Welcome")
        return context


def handler404(request, exception):
    return render(request, "404.html", status=404)


def handler400(request, exception):
    return render(request, "400.html", status=400)


def handler500(request):
    return render(request, "500.html", status=500)
