from datetime import datetime

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.translation import gettext as _

from virtual_library_card.sender import Sender
from virtual_library_card.smarty_streets import AddressChecker
from VirtualLibraryCard.models import CustomUser, Library, LibraryCard


class RequestLibraryCardForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = CustomUser
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

        widgets = {
            "library": forms.HiddenInput(),
            "country_code": forms.HiddenInput(),
            # 'us_state': forms.HiddenInput(),
        }
        readonly_fields = ("library", "country_code")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.pop("autofocus", None)
        self.fields["us_state"].widget.attrs["disabled"] = True
        self.fields["over13"].required = True
        self.fields["first_name"].required = True

        user = kwargs["instance"]
        library: Library = user.library
        if library.patron_address_mandatory == False:
            self.fields["street_address_line1"].required = False
            self.fields["city"].required = False
            self.fields["zip"].required = False

        # Focus on form field whenever error occurred
        error_list = list(self.errors)
        print("------------ ERRORS: ", error_list)
        if error_list:
            for item in error_list:
                self.fields[item].widget.attrs.update({"autofocus": ""})
                break
        else:
            self.fields["first_name"].widget.attrs["autofocus"] = "autofocus"

    def get_form_kwargs(self):
        kwargs = super(RequestLibraryCardForm, self).get_form_kwargs()

        return kwargs

    def validate_unique(self):
        form_email = self.cleaned_data.get("email")
        existing_user: CustomUser = CustomUser.objects.filter(email=form_email).first()
        if existing_user is None:
            try:
                first_name = self.cleaned_data.get("first_name")
                if not first_name:
                    self.add_error("first_name", _("First name is mandatory"))
                    raise forms.ValidationError(_("Please enter your first name"))
                last_name = self.cleaned_data.get("last_name")
                street_address_line1 = self.cleaned_data.get("street_address_line1")
                street_address_line2 = self.cleaned_data.get("street_address_line2")
                city = self.cleaned_data.get("city")
                us_state = self.cleaned_data.get("us_state")
                zip = self.cleaned_data.get("zip")

                library: Library = self.cleaned_data.get("library")
                if library.patron_address_mandatory:
                    is_valid_address = AddressChecker.is_valid_postal_address(
                        first_name,
                        last_name,
                        street_address_line1,
                        street_address_line2,
                        city,
                        us_state,
                        zip,
                    )
                else:
                    is_valid_address = True
                # is_valid_address = True
                # FOR DEV PURPOSE ONLY
                if is_valid_address:
                    super().validate_unique()
                else:
                    self.add_error(
                        "street_address_line1", _("Please check all address fields")
                    )
                    raise forms.ValidationError(
                        _("The address you entered does not seem to be correct")
                    )
            except ValidationError as e:
                self._update_errors(e)

    def save(self, commit=True):
        form_email = self.cleaned_data.get("email")
        library = self.cleaned_data.get("library")
        print(form_email, "form_email")
        existing_user: CustomUser = CustomUser.objects.filter(email=form_email).first()

        print(existing_user, "existing_user")
        try:
            if existing_user:
                print("*******user exists")
                existing_user.library = library
                existing_user.save()
                user = existing_user
            else:
                print("user do not exists")
                user: CustomUser = super().save(commit=False)
                user.library = library
                user: CustomUser = super().save(commit=True)

            if user:
                existing_library_card: LibraryCard = LibraryCard.objects.filter(
                    user=existing_user, library=library
                ).first()
                if existing_library_card:
                    if (
                        existing_library_card.canceled_date is not None
                        or existing_library_card.is_expired()
                    ):
                        reactivate_library_card(existing_library_card)
                        Sender.send_user_welcome(
                            library, user, existing_library_card.number
                        )
                    else:
                        a_library_card_message = _(
                            "The library card for the %(library_name)s"
                            % {"library_name": "<strong>" + library.name + "</strong>"}
                        )
                        with_email = _(
                            "and the email %(form_email)s"
                            % {"form_email": "<strong>" + form_email + "</strong>"}
                        )
                        message = (
                            a_library_card_message
                            + " "
                            + with_email
                            + " "
                            + _("already exists")
                        )
                        raise forms.ValidationError(
                            _("The library card has not been created"),
                            code="ALREADY_EXISTS",
                            params={"custom_message": message},
                        )

                else:
                    library_card = CustomUser.create_card_for_library(library, user)
                    library_card.save()
                    print("-----------saved library_card")
                    Sender.send_user_welcome(library, user, library_card.number)
                    print("-----------email sent to user")
                    return user
            else:
                raise forms.ValidationError(_("Error creating your library card"))
        except ValidationError as e:
            self._update_errors(e)


class SignupCardForm(forms.Form):
    lat = forms.CharField(widget=forms.TextInput())
    long = forms.CharField(widget=forms.TextInput())
    identifier = forms.CharField(widget=forms.TextInput())


class LibraryCardDeleteForm(forms.ModelForm):
    class Meta(ModelForm):
        model = LibraryCard
        fields = ["id", "number", "canceled_date", "canceled_by_user"]

    def save(self, commit=True):
        number = self.cleaned_data.get("number")
        library_card: LibraryCard = LibraryCard.objects.filter(number=number).first()
        library: Library = library_card.library
        if library_card:
            user = library_card.user
            all_user_library_cards = LibraryCard.objects.filter(user=user)
            library_card.canceled_date = datetime.today()
            library_card.canceled_by_user = user.username
            library_card = library_card.save()
            # I UPDATE THE USER LIBRARY (USED FOR BRANDING) IF REQUIRED
            update_user_library(self, user, library, all_user_library_cards)

        else:
            print("library_card with this number not exist any more", number)

        return super().save(commit=True)


def update_user_library(self, user, library, all_user_library_cards):
    # I UPDATE THE USER LIBRARY (USED FOR BRANDING) IF REQUIRED
    if all_user_library_cards.count() > 1 and user.library.id == library.id:
        active_library_card = LibraryCard.objects.filter(
            user=user, canceled_date=None
        ).first()
        if active_library_card:
            user.library = active_library_card.library
            user.save()
    return user


def reactivate_library_card(canceled_library_card):
    print("============ reactivate_library_card")
    canceled_library_card.canceled_date = None
    canceled_library_card.canceled_by_user = None
    canceled_library_card.expiration_date = None
    canceled_library_card.save()
    return canceled_library_card
