from datetime import UTC, datetime

from django import forms
from django.apps import apps
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.translation import gettext as _
from django_recaptcha.fields import ReCaptchaField

from virtual_library_card.logging import LoggingMixin
from virtual_library_card.sender import Sender
from virtuallibrarycard.business_rules.library_card import LibraryCardRules
from virtuallibrarycard.models import CustomUser, Library, LibraryCard, UserConsent


class RequestLibraryCardForm(LoggingMixin, UserCreationForm):
    CONSENT_TYPE = UserConsent.ConsentType.SURVEY
    CONSENT_METHOD = UserConsent.ConsentMethod.WEB_CARD_REQUEST
    consent = forms.fields.BooleanField(
        required=False,
        label=_(UserConsent.consent_text[CONSENT_TYPE]),
        initial="on",
    )

    class Meta(UserCreationForm):
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "email",
            "library",
            "over13",
        ]

        widgets = {
            "library": forms.HiddenInput(),
        }
        readonly_fields = "library"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.pop("autofocus", None)
        self.fields["over13"].required = True
        self.fields["first_name"].required = True

        # keep the captcha part dynamic, in case captcha is not supported
        if apps.is_installed("django_recaptcha"):
            self.fields["captcha"] = ReCaptchaField()

        user = kwargs["instance"]
        library: Library = user.library

        # Disable consent field if the library does not need it
        if library and not library.has_survey_consent:
            consent: forms.BooleanField = self.fields["consent"]
            consent.initial = None
            consent.disabled = True
            consent.widget = consent.hidden_widget()

        if library.age_verification_mandatory is False:
            # Don't show this in case we don't need age verification
            self.fields["over13"].required = False
            self.fields["over13"].widget = forms.HiddenInput()

        # Focus on form field whenever error occurred
        error_list = list(self.errors)
        if error_list:
            for item in error_list:
                self.fields[item].widget.attrs.update({"autofocus": ""})
                break
        else:
            self.fields["first_name"].widget.attrs["autofocus"] = "autofocus"

    def validate_unique(self):
        form_email = self.cleaned_data.get("email")
        existing_user: CustomUser = CustomUser.objects.filter(
            email__iexact=form_email
        ).first()
        if existing_user is None:
            try:
                first_name = self.cleaned_data.get("first_name")
                if not first_name:
                    self.add_error("first_name", _("First name is mandatory"))
                    raise forms.ValidationError(_("Please enter your first name"))

            except ValidationError as e:
                self._update_errors(e)
        else:
            self.add_error("email", _("Email address already in use"))

    def save(self, commit=True):
        form_email = self.cleaned_data.get("email")
        library = self.cleaned_data.get("library")
        existing_user: CustomUser = CustomUser.objects.filter(email=form_email).first()
        # User consent
        consent = self.cleaned_data.get("consent")

        try:
            if existing_user:
                existing_user.library = library
                existing_user.save()
                user = existing_user
            else:
                user: CustomUser = super().save(commit=False)
                user.library = library
                user.email_verified = (
                    False  # If this is a new user, email is not verified yet
                )
                user: CustomUser = super().save(commit=True)

            if user:
                if consent is True:
                    try:
                        UserConsent.record_consent(
                            user, self.CONSENT_TYPE, self.CONSENT_METHOD
                        )
                    except ValueError as ex:
                        # Log error and continue with the sign up
                        self.log.error(
                            f"Could not record user consent for {user.email} ({self.CONSENT_TYPE}, {self.CONSENT_METHOD}): {ex}"
                        )

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
                            library, user, card_number=existing_library_card.number
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
                    card, _ = LibraryCardRules.new_card(user, library)
                    card.save()
                    return user
            else:
                raise forms.ValidationError(_("Error creating your library card"))

        except ValidationError as e:
            self._update_errors(e)


class SignupCardForm(forms.Form):
    lat = forms.CharField(widget=forms.TextInput())
    long = forms.CharField(widget=forms.TextInput())
    identifier = forms.CharField(widget=forms.TextInput())


class LibraryCardDeleteForm(LoggingMixin, forms.ModelForm):
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
            library_card.canceled_date = datetime.now(UTC)
            library_card.canceled_by_user = user.username
            library_card = library_card.save()
            # I UPDATE THE USER LIBRARY (USED FOR BRANDING) IF REQUIRED
            update_user_library(self, user, library, all_user_library_cards)

        else:
            self.log.debug(
                f"library_card with this number does not exist any more {number}"
            )

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
    canceled_library_card.canceled_date = None
    canceled_library_card.canceled_by_user = None
    canceled_library_card.expiration_date = None
    canceled_library_card.save()
    return canceled_library_card
