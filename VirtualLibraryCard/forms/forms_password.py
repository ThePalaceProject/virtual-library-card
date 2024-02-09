from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.contrib.auth.forms import (
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.utils.translation import gettext as _

from VirtualLibraryCard.forms import ValidationError
from VirtualLibraryCard.models import CustomUser


class CustomPasswordChangeForm(PasswordChangeForm):
    class Meta(PasswordChangeForm):
        model = CustomUser

    fields = ["email", "password"]
    helper = FormHelper()
    helper.add_input(
        Submit("submit", _("Save"), css_class="btn-primary", aria_label=_("Save"))
    )
    helper.form_method = "POST"


class CustomSetPasswordForm(SetPasswordForm):
    class Meta(SetPasswordForm):
        model = CustomUser

    fields = ["email", "password"]
    helper = FormHelper()
    helper.add_input(
        Submit("submit", _("Save"), css_class="btn-primary", aria_label=_("Save"))
    )
    helper.form_method = "POST"


class CustomPasswordResetForm(PasswordResetForm):
    class Meta(PasswordResetForm):
        model = CustomUser

    fields = ["email"]

    helper = FormHelper()
    helper.add_input(
        Submit("submit", _("Save"), css_class="btn-primary", aria_label=_("Save"))
    )
    helper.form_method = "POST"

    def clean_email(self):
        email = self.cleaned_data["email"]
        if not CustomUser.objects.filter(email__iexact=email, is_active=True).exists():
            raise ValidationError(
                _(
                    "There is no user registered with the specified email address %(email)s"
                )
                % {"email": email}
            )

        return email
