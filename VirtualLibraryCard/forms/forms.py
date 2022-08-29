from gettext import gettext as _

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.forms.utils import ErrorList
from django.utils.safestring import mark_safe
from localflavor.us.forms import USStateSelect

from virtual_library_card.logging import LoggingMixin
from virtual_library_card.sender import Sender
from VirtualLibraryCard.business_rules.library import LibraryRules
from VirtualLibraryCard.models import CustomUser, Library, LibraryCard


class LibraryCreationForm(forms.ModelForm):
    class Meta:
        model = Library
        exclude = []


class LibraryCardCreationForm(forms.ModelForm):
    class Meta:
        model = LibraryCard
        exclude = []
        labels = {"user": _("User Email")}


class LibraryChangeForm(forms.ModelForm):
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
    class Media:
        css = {"all": ("css/admin.css",)}

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
            existing_library_card: LibraryCard = LibraryCard.objects.filter(
                user=user, library=library
            ).first()
            if existing_library_card is None:
                try:
                    self.log.debug("-----------before creating card")
                    library_card = CustomUser.create_card_for_library(library, user)
                    self.log.debug("-----------before saving")
                    library_card.save()
                    self.created_library_card = library_card  # used by the view
                    self.log.debug("-----------saved library_card")
                    Sender.send_user_welcome(library, user, library_card.number)
                except Exception as e:
                    self.log.error(f"Exception {e}")

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
