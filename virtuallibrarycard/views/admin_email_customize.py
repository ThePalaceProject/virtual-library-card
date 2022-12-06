from gettext import gettext as _
from typing import Any, Dict

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.template import Context, Engine
from django.views.generic import FormView

from virtuallibrarycard.models import Library


class CustomizeWelcomeEmailForm(forms.Form):
    top_text = forms.CharField(widget=forms.Textarea(), required=False)
    bottom_text = forms.CharField(widget=forms.Textarea(), required=False)

    helper = FormHelper()
    helper.add_input(
        Submit("submit", _("Save"), css_class="btn-primary", aria_label=_("Save"))
    )
    helper.form_method = "POST"


class AdminCustomizeWelcomeEmailView(PermissionRequiredMixin, FormView):
    form_class = CustomizeWelcomeEmailForm
    template_name: str = "admin/customize_welcome_email.html"
    email_template = "email/welcome_user.html"

    def has_permission(self) -> bool:
        if self.request.user.is_superuser:
            return True
        elif self.request.user.is_staff:
            return self.request.user.library == self._get_url_library()

        return False

    def _get_url_library(self):
        """Get a library instance from the /<id>/ url parameter"""
        library_id = self.kwargs["id"]
        return Library.objects.get(id=library_id)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """The context data needs the email template rendered string
        so the javascript may show a preview to the user"""
        ctx = super().get_context_data(**kwargs)

        # Render the email template, with special replaceable characters
        engine = Engine.get_default()
        template = engine.get_template(self.email_template)
        library = self._get_url_library()
        email_str = template.render(
            Context(
                {
                    "library": library,
                    "link": "#link",
                    "verification_link": "#verification",
                    "card_number": "#######",
                    "login_url": "#login",
                    "has_welcome": True,
                    "has_verification": True,
                    "custom_top_text": "[[CUSTOM_TOP_TEXT]]",  # easy to search and replace
                    "custom_bottom_text": "[[CUSTOM_BOTTOM_TEXT]]",  # easy to search and replace
                }
            )
        )
        ctx["email_str"] = email_str

        return ctx

    def get_initial(self) -> Dict[str, Any]:
        """The intitial form data should be prefilled with the saved text"""
        library = self._get_url_library()
        return {
            "top_text": library.customization.welcome_email_top_text,
            "bottom_text": library.customization.welcome_email_bottom_text,
        }

    def form_valid(self, form) -> HttpResponse:
        library = self._get_url_library()

        # Do not access cleaned data, it trims extra spaces, which may be on purpose
        top_text = form.data.get("top_text")
        bottom_text = form.data.get("bottom_text")

        library.customization.welcome_email_top_text = top_text
        library.customization.welcome_email_bottom_text = bottom_text
        library.customization.save()
        return self.render_to_response(self.get_context_data())
