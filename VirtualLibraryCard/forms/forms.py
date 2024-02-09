from gettext import gettext as _

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.forms.utils import ErrorList
from django.utils.safestring import mark_safe
from localflavor.us.forms import USStateSelect

from virtual_library_card.sender import Sender
from VirtualLibraryCard.models import CustomUser, Library, LibraryCard


class LibraryCreationForm(forms.ModelForm):
    class Meta:
        model = Library
        exclude = []


class LibraryCardCreationForm(forms.ModelForm):
    class Meta:
        model = LibraryCard
        exclude = []

    def validate_unique(self):
        print("validate_unique")
        libraryCard = self.instance

        super().validate_unique()


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


class CustomAdminUserChangeForm(UserChangeForm):
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
        exclude = ["password"]
        readonly_fields = ["email"]

    def library_cards(self):
        return self.model.library_cards

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
                self.fields["first_name"].widget.attrs["disabled"] = True

        except KeyError as e:
            print("Error disabling email and first name", e)

        try:
            self.fields["library"].required = True

        except KeyError as e:
            print("Library field is not editable")

    def get_form(self, request, obj=None, **kwargs):
        if self.request.user.is_superuser:
            self.exclude.append("Permissions")  # here!
        if obj:
            self.fields["email"].value = obj.email
        super().get_form(request, obj, **kwargs)

    def save(self, commit=True):
        print("-----------before save CustomAdminUserChangeForm")
        user: CustomUser = super().save(commit)
        print("user ", user)
        library = user.library
        if library:
            print("library ", library)
            existing_library_card: LibraryCard = LibraryCard.objects.filter(
                user=user, library=library
            ).first()
            if existing_library_card is None:
                try:
                    print("-----------before creating card")
                    library_card = CustomUser.create_card_for_library(library, user)
                    print("-----------before saving")
                    library_card.save()
                    print("-----------saved library_card")
                    Sender.send_user_welcome(library, user, library_card.number)
                except Exception as e:
                    print("Exception", e)

        return user
