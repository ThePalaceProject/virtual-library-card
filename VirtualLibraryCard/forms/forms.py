from gettext import gettext as _
from typing import Any, Dict, Optional

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.forms.utils import ErrorList
from django.utils.safestring import mark_safe
from localflavor.us.forms import USStateSelect

from virtual_library_card.logging import LoggingMixin
from VirtualLibraryCard.business_rules.library import LibraryRules
from VirtualLibraryCard.business_rules.library_card import LibraryCardRules
from VirtualLibraryCard.models import CustomUser, Library, LibraryCard
from VirtualLibraryCard.widgets.buttons import LinkButtonField


class LibraryCreationForm(forms.ModelForm):
    class Meta:
        model = Library
        exclude = []


class LibraryCardCreationForm(forms.ModelForm):
    class Meta:
        model = LibraryCard
        exclude = []
        labels = {"user": _("User Email")}

    def __init__(self, data: Dict = None, *args, **kwargs) -> None:
        super().__init__(data, *args, **kwargs)

        # If we have the field and also have a new instance (on create)
        number = self.fields.get("number")
        if number and not (self.instance and self.instance.pk):
            number.required = False
            number.help_text = _(
                "The card number will be automatically generated if it is not provided already.\
                <br>In case a number is provided it will be prefixed by the Library prefix"
            )

    def clean(self) -> Optional[Dict[str, Any]]:
        super().clean()
        number = self.cleaned_data.get("number")
        if not self.instance.pk and number:
            library = self.cleaned_data["library"]
            self.cleaned_data["number"] = library.prefix + number

        return self.cleaned_data

    def validate_unique(self) -> None:
        """validate if the manually entered card number is unique"""
        super().validate_unique()
        if self.cleaned_data.get("number"):
            library = self.cleaned_data["library"]
            exists = LibraryCard.objects.filter(
                number=self.cleaned_data["number"], library=library
            ).exists()
            if exists:
                self.add_error("number", "This number already exists for this library")


class LibraryChangeForm(forms.ModelForm):

    Customize_emails_field = LinkButtonField("../welcome_email/update")

    class Meta:
        model = Library
        exclude = []
        widgets = {
            "yes_or_no": forms.RadioSelect,
        }

    def __init__(
        self,
        data=None,
        files=None,
        auto_id="id_%s",
        prefix=None,
        initial=None,
        error_class=ErrorList,
        label_suffix=None,
        empty_permitted=False,
        instance=None,
        use_required_attribute=None,
        renderer=None,
    ):
        super().__init__(
            data,
            files,
            auto_id,
            prefix,
            initial,
            error_class,
            label_suffix,
            empty_permitted,
            instance,
            use_required_attribute,
            renderer,
        )
        if self.instance.logo:
            self.fields["logo"].help_text = mark_safe(
                '<img src="{url}" alt="{alt}" aria-label="{alt}" width="100" />'.format(
                    url=self.instance.logo.url, alt=self.instance.name + " logo"
                )
            )
        self.fields["sequence_down"].label = _("Sequence order")

        # Customisation button setup
        emails_field: LinkButtonField = self.fields["Customize_emails_field"]
        emails_field.initial = _("Update")
        emails_field.label = _("Welcome Email")
        emails_field.help_text = _(
            "Add some custom text to the welcome emails sent to new patrons."
        )


class LibraryCardChangeForm(forms.ModelForm):
    sequence_down = forms.TypedChoiceField(
        coerce=lambda x: bool(int(x)),
        choices=((0, "Up"), (1, "Down")),
        widget=forms.RadioSelect,
    )

    class Meta:
        model = LibraryCard
        exclude = []

    def save(self, commit=True):
        library_card: LibraryCard = super(LibraryCardCreationForm).save(commit)
        if library_card.library.id != library_card.user.library.id:
            library_card.user.library = library_card.library
            library_card.user.save(commit)
        return library_card


class CustomUserCreationForm(UserCreationForm):
    email = forms.CharField(initial="")
    first_name = forms.CharField(initial="")

    class Meta(UserCreationForm):
        model = CustomUser
        state = forms.CharField(widget=USStateSelect)
        fields = [
            "first_name",
            "last_name",
            "email",
            "street_address_line1",
            "street_address_line2",
            "city",
            "zip",
            "us_state",
            "library",
            "country_code",
            "over13",
        ]


class CustomAdminUserChangeForm(LoggingMixin, UserChangeForm):
    class Meta(UserChangeForm):
        model = CustomUser
        state = forms.CharField(widget=USStateSelect)
        fields = [
            "first_name",
            "last_name",
            "email",
            "over13",
            "street_address_line1",
            "street_address_line2",
            "city",
            "zip",
            "library",
            "user_permissions",
        ]
        readonly_fields = ["email"]

    def library_cards(self):
        return self.model.library_cards

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created_library_card = None

        # Customize the password change link UI
        password = self.fields.get("password")
        if password:
            password.help_text = "<span class='password-help'><a href='../password'>CHANGE PASSWORD</a></span>"

        try:
            instance = getattr(self, "instance", None)
            if (
                instance and not instance.us_state
            ):  # Edition just after creation form with minimal fields
                self.fields[
                    "email"
                ].widget.value_from_datadict = lambda *args: self.instance.email
                self.fields[
                    "first_name"
                ].widget.value_from_datadict = lambda *args: self.instance.first_name
                self.fields["email"].widget.attrs["disabled"] = True

        except KeyError as e:
            self.log.error(f"Error disabling email and first name {e}")

        if instance and instance.library.age_verification_mandatory == False:
            # Don't show this in case we don't need age verification
            self.fields["over13"].widget = forms.HiddenInput()

        try:
            self.fields["library"].required = True

        except KeyError as e:
            self.log.error(f"Library field is not editable {e}")

        self.fields["street_address_line1"].required = False
        self.fields["city"].required = False
        self.fields["zip"].required = False

    def get_form(self, request, obj=None, **kwargs):
        if self.request.user.is_superuser:
            self.exclude.append("Permissions")  # here!
        if obj:
            self.fields["email"].value = obj.email
        super().get_form(request, obj, **kwargs)

    def save(self, commit=True):
        self.log.debug("-----------before save CustomAdminUserChangeForm")
        user: CustomUser = super().save(commit)
        self.log.debug(f"user {user}")
        library = user.library
        if library:
            self.log.debug(f"library {library}")
            card, is_new = LibraryCardRules.new_card(user, library)
            if is_new:
                self.created_library_card = card

        return user

    def is_valid(self) -> bool:
        email = self.data.get("email", self.instance.email)
        library_id = self.data.get("library")
        if library_id:
            # Fake user with the right info, unsaved
            user = CustomUser(email=email, library=Library.objects.get(id=library_id))
            if not user.is_valid_email_domain():
                self.add_error("email", _("Invalid email domain"))
                return False

            # validate the zip/state fields on user edit
            current_user = self.instance
            library: Library = current_user.library

            # If the state was edited, the user must reside within the library defined states
            us_state = self.data.get("us_state")
            zip = self.data.get("zip")
            city = self.data.get("city")

            validation = LibraryRules.validate_user_address_fields(
                library, us_state=us_state, zip=zip, city=city
            )
            if not validation.us_state_valid:
                self.add_error(
                    "us_state",
                    _(
                        f"The user must be within the library defined states: {','.join(library.get_us_states())}"
                    ),
                )
                return False

            if not validation.zip_valid:
                self.add_error("zip", _(f"The zip is not valid for this address"))
                return False

        return super().is_valid()


class LibraryCardsUploadByCSVForm(forms.Form):

    library = forms.ChoiceField()
    csv_file = forms.FileField()

    def __init__(self, data=None, **kwargs) -> None:
        super().__init__(data, **kwargs)
        library_field: forms.Select = self.fields.get("library")
        library_field.choices = [
            (l.id, l.name) for l in Library.objects.filter(allow_bulk_card_uploads=True)
        ]
        if not library_field.choices:
            library_field.choices = [(0, "No Library allows bulk uploads")]

        self.helper = FormHelper()
        self.helper.add_input(
            Submit("Start the CSV Upload job", "Start the CSV Upload job")
        )
