from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView, PasswordResetView
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from VirtualLibraryCard.forms.forms_password import (
    CustomPasswordChangeForm,
    CustomPasswordResetForm,
)
from VirtualLibraryCard.models import CustomUser


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    model = CustomUser
    form_class = CustomPasswordChangeForm
    template_name = "accounts/password/change_password.html"
    success_url = "password_change_done"

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class PasswordChangeDoneView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/password/password_change_done.html"


class CustomResetPasswordView(PasswordResetView):
    model = CustomUser
    form_class = CustomPasswordResetForm
    template_name = "registration/reset_password.html"

    def get_form_kwargs(self):
        return super().get_form_kwargs()

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        existing_user = CustomUser.objects.filter(email=email).first()
        message = ""
        if existing_user and existing_user.library:
            message = _(
                "If you did not receive an email contact %(library_name)s at %(email)s"
                % {
                    "library_name": existing_user.library.name,
                    "email": existing_user.library.email,
                }
            )

        messages.success(self.request, message)
        return super().form_valid(form)
