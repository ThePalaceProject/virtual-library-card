from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView, PasswordResetView
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from virtuallibrarycard.forms.forms_password import (
    CustomPasswordChangeForm,
    CustomPasswordResetForm,
)
from virtuallibrarycard.models import CustomUser, LibraryCard


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
    html_email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"

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

            # Get all library cards associated with the user's email address
            # Query by user's email to ensure we get the correct user's cards
            # even if the user object is a different instance
            library_cards = list(LibraryCard.objects.filter(
                user__email=existing_user.email,
                canceled_date__isnull=True
            ).select_related('library').order_by('created'))

            if not self.extra_email_context:
                self.extra_email_context = {}

            self.extra_email_context['library_cards'] = library_cards

        messages.success(self.request, message)
        return super().form_valid(form)
