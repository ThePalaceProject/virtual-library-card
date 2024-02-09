from gettext import gettext as _
from typing import Any, Dict, Optional

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from dal import autocomplete
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.forms.utils import ErrorList
from django.utils.safestring import mark_safe
from localflavor.us.forms import USStateSelect

from virtual_library_card.logging import LoggingMixin
from virtuallibrarycard.business_rules.library_card import LibraryCardRules
from virtuallibrarycard.models import (
    CustomUser,
    Library,
    LibraryCard,
    LibraryPlace,
    Place,
)
from virtuallibrarycard.widgets.buttons import LinkButtonField


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
    places_filter = forms.ModelMultipleChoiceField(
        queryset=Place.objects.all(),
        widget=FilteredSelectMultiple("Library Places", False),
        required=False,
        label="",
    )

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

        # Customisation button setup
        emails_field: LinkButtonField = self.fields["Customize_emails_field"]
        emails_field.initial = _("Update")
        emails_field.label = _("Welcome Email")
        emails_field.help_text = _(
            "Add some custom text to the welcome emails sent to new patrons."
        )

        self.fields["bulk_upload_prefix"].required = False
        self.fields["bulk_upload_prefix"].help_text = _(
            "This field is only required when Bulk Card Uploads are enabled."
        )

        self.fields["uuid"].help_text = _(
            "The Library UUID should be a globally unique UUID provided by the Library Registry."
            "<br>If not provided, on email verification, the user will not be redirected to the Mobile Apps."
        )

        # The initial set of library places
        if self.instance.pk:
            self.fields["places_filter"].initial = self.instance.places

    def is_valid(self) -> bool:
        valid = super().is_valid()

        # If the bulk uploads are allowed we must have a prefix set for them
        if self.cleaned_data["allow_bulk_card_uploads"] is True:
            if not self.cleaned_data.get("bulk_upload_prefix"):  # None or empty
                valid = False
                self.add_error(
                    "bulk_upload_prefix",
                    "When bulk card uploads are allowed, this field must be given a value.",
                )

        return valid

    def _save_m2m(self) -> Any:
        # Add new places selected and remove anything unselected.
        # We have to do this because we created a relation table manually
        # and not a ManyToMany field in the Library model.
        # Changing this now would lead to loss of data so we'll manage this widget manually.
        # At this point we can assume the model has been saved.
        prev = self.instance.places

        for p in self.cleaned_data["places_filter"]:
            if p not in prev:
                # A new place was added
                LibraryPlace(library=self.instance, place=p).save()
            else:
                # This was in the list and selected, remove this from the list
                prev.remove(p)
        # Anything left over should get deleted
        for p in prev:
            LibraryPlace.objects.filter(library=self.instance, place=p).delete()

        return super()._save_m2m()


class LibraryCardChangeForm(forms.ModelForm):
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
            "place",
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
        self.user = kwargs.get("user")

        # Customize the password change link UI
        password = self.fields.get("password")
        if password:
            password.help_text = "<span class='password-help'><a href='../password'>CHANGE PASSWORD</a></span>"

        is_active = self.fields.get("is_active")
        if is_active:
            is_active.label = "Active User status"
            is_active.help_text = "Assigning the active setting doesn't mean that the user will be allowed to log in to the admin site"

        is_superuser = self.fields.get("is_superuser")
        if is_superuser:
            is_superuser.label = "VLC Super Administrator status"

        try:
            instance = getattr(self, "instance", None)
            if (
                instance and not instance.place
            ):  # Edition just after creation form with minimal fields
                self.fields["email"].widget.value_from_datadict = (
                    lambda *args: self.instance.email
                )
                self.fields["first_name"].widget.value_from_datadict = (
                    lambda *args: self.instance.first_name
                )
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

        if "place" in self.fields:
            self.fields["place"].label = "State"
            self.fields["place"].queryset = Place.objects.filter(
                type__in=(Place.Types.STATE, Place.Types.PROVINCE)
            )

    def save(self, commit=True):
        user: CustomUser = super().save(commit)
        library = user.library
        if library:
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

        return super().is_valid()


class LibraryCardsUploadByCSVForm(forms.Form):
    library = forms.ChoiceField()
    csv_file = forms.FileField()

    def __init__(self, user, data=None, **kwargs) -> None:
        super().__init__(data, **kwargs)
        library_field: forms.Select = self.fields.get("library")

        # If a user is not a superuser only provide the library which the user belongs to.
        query = Library.objects.filter(allow_bulk_card_uploads=True)
        if not user.is_superuser:
            query = query.filter(id=user.library.id)

        library_field.choices = [(l.id, l.name) for l in query]
        if not library_field.choices:
            library_field.choices = [(0, "No Library allows bulk uploads")]

        self.helper = FormHelper()
        self.helper.add_input(
            Submit("Start the CSV Upload job", "Start the CSV Upload job")
        )


class CustomPlaceChangeForm(forms.ModelForm):
    name = autocomplete.Select2ListCreateChoiceField(
        widget=autocomplete.ListSelect2(
            url="place_typeahead",
            attrs={
                "data-minimum-input-length": 2,
                "data-placeholder": "Search for a place",
            },
        )
    )

    class Meta:
        model = Place
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # DAL doesn't have the ability to prepopulate the Select2ListCreateChoiceField when editing Place
        # so we need to do it manually.
        if self.instance:
            # If we already have instance of the form i.e. we are editing the Place.
            place_name = self.instance.name

            self.fields["name"].initial = place_name
            self.fields["name"].choices = [(place_name, place_name)]
