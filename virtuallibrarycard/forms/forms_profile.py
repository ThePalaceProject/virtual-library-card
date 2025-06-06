from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.contrib.auth.forms import UserChangeForm
from django.forms import HiddenInput
from django.utils.translation import gettext as _

from virtuallibrarycard.models import CustomUser


class ProfileEditForm(UserChangeForm):
    class Meta(UserChangeForm):
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
        ]

    helper = FormHelper()
    helper.add_input(
        Submit("submit", _("Save"), css_class="btn-primary", aria_label=_("Save"))
    )
    helper.form_method = "POST"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].widget = HiddenInput()
