from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from pathlib import Path

import datedelta
import django.utils.timezone
from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.validators import RegexValidator
from django.db import models
from django.templatetags.static import static
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from virtual_library_card.card_number import CardNumber


def boolean_choices():
    return ((True, _("Yes")), (False, _("No")))


def value_to_link(_value, _display_label):
    if _value is not None:
        return '<a href="' + _value + '" target="_blank" >' + _display_label + "</a>"
    return ""


class LowerCharField(models.CharField):
    """CharField like column, but forces values to lowercase before saving to the DB"""

    def get_prep_value(self, value: str) -> str:
        value = value.lower()
        return super().get_prep_value(value)


class LibraryCustomization(models.Model):
    """Adding all text based customization in a different table
    so that large chunks of data are not read on every access
    """

    welcome_email_top_text = models.TextField(max_length=512, null=True, blank=True)
    welcome_email_bottom_text = models.TextField(max_length=512, null=True, blank=True)


def default_customization():
    lc = LibraryCustomization()
    lc.save()
    return lc.id


class Library(models.Model):
    class Meta:
        verbose_name_plural = "libraries"

    @staticmethod
    def create_default_library():
        library = Library(
            name=settings.DEFAULT_SUPERUSER_LIBRARY_NAME,
            identifier=settings.DEFAULT_SUPERUSER_LIBRARY_IDENTIFIER,
            prefix=settings.DEFAULT_SUPERUSER_LIBRARY_PREFIX,
        )
        library.save()

        # Load the library-place if it is present
        place = Place.objects.filter(
            abbreviation=settings.DEFAULT_SUPERUSER_LIBRARY_STATE
        ).first()
        if place is not None:
            lp = LibraryPlace(library=library, place=place)
            lp.save()

        return library

    def generate_filename(self, filename):
        return f"library/logo_{self.identifier}{Path(filename).suffix}"

    BOOL_CHOICES = ((True, _("Descending")), (False, _("Ascending")))

    name = models.CharField(max_length=255, null=True, blank=False)
    identifier = models.CharField(max_length=255, null=True, blank=False, unique=True)
    uuid = models.CharField(max_length=255, null=True, blank=True, unique=True)

    logo = models.ImageField(upload_to=generate_filename, null=True, blank=False)
    phone = models.CharField(max_length=50, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    terms_conditions_url = models.CharField(max_length=255, blank=False)
    privacy_url = models.CharField(
        max_length=255, null=False, blank=False, default=settings.DEFAULT_PRIVACY_URL
    )
    social_facebook = models.CharField(max_length=255, null=True, blank=True)
    social_twitter = models.CharField(max_length=255, null=True, blank=True)
    prefix = models.CharField(max_length=10, null=True, blank=False)
    bulk_upload_prefix = models.CharField(max_length=10, null=True, blank=False)
    card_validity_months = models.PositiveSmallIntegerField(null=True, blank=True)
    sequence_start_number = models.IntegerField(default=0)
    sequence_end_number = models.IntegerField(null=True, blank=True)
    sequence_down = models.BooleanField(
        choices=BOOL_CHOICES, blank=False, null=False, default=False
    )

    # Configurables
    patron_address_mandatory = models.BooleanField(
        choices=boolean_choices(),
        blank=False,
        default=True,
        verbose_name="Require Patron Address",
    )
    barcode_text = models.CharField(
        max_length=255, default="barcode", verbose_name="Barcode Text"
    )
    pin_text = models.CharField(max_length=255, default="pin", verbose_name="Pin Text")
    age_verification_mandatory = models.BooleanField(
        choices=boolean_choices(),
        blank=False,
        default=True,
        verbose_name="Require Patron Age Verification",
    )
    allow_bulk_card_uploads = models.BooleanField(
        choices=boolean_choices(),
        blank=False,
        default=False,
        verbose_name="Allow Bulk Upload For Library Cards",
    )

    customization = models.ForeignKey(
        LibraryCustomization,
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        unique=True,
        related_name="library",
        default=default_customization,
    )

    has_survey_consent = models.BooleanField(
        verbose_name="Marketing Consent", default=False, choices=boolean_choices()
    )

    @property
    def places(self):
        """Get places related to this library"""
        return [ls.place for ls in self.library_places.order_by("id").all()]

    def get_places(self):
        return [
            (ls.place.abbreviation or ls.place.name)
            for ls in self.library_places.order_by("id").all()
        ]

    def get_first_place(self):
        try:
            return self.get_places()[0]
        except IndexError:
            return None

    def get_logo_img(self, logo_url, header):
        img_html = '<img alt="{} logo" aria-label="{} logo" src="{}"{}/>'

        if header:
            additional = ' class="logo"'
        else:
            additional = ' width="100px"'

        return mark_safe(img_html.format(self.name, self.name, logo_url, additional))

    def logo_thumbnail(self):
        return self.get_logo_img(self.logo_url(), False)

    def logo_url(self):
        if self.logo:
            return default_storage.url(str(self.logo))
        else:
            return static("images/logo.png")

    def logo_header(self):
        return self.get_logo_img(self.logo_url(), True)

    def state_name(self):
        try:
            return self.library_places.first().place.name
        except AttributeError:
            return None

    def social_links(self):
        global_links = ""
        if self.social_facebook is not None:
            global_links += value_to_link(self.social_facebook, "FB")
        if self.social_twitter is not None:
            if self.social_facebook is not None:
                global_links += "<br/>"
            global_links += value_to_link(self.social_twitter, "Twitter")
        return mark_safe(global_links)

    def terms_conditions_link(self):
        return mark_safe(value_to_link(self.terms_conditions_url, _("See")))

    def __str__(self):
        return self.name

    def get_allowed_email_domains(self) -> list[str]:
        return [e.domain for e in self.library_email_domains.all()]


class LibraryPlace(models.Model):
    """Library to Place relation"""

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["library", "place"], name="unique_library_place"
            )
        ]

    library = models.ForeignKey(
        Library,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="library_places",
    )
    place = models.ForeignKey(
        "Place",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="place_libraries",
    )

    @classmethod
    def associate(cls, library: Library, place_abbreviation: str) -> LibraryPlace:
        """Associate a library with a 'place' via abbreviation notation
        Only if it does not exist already"""
        place = Place.objects.get(abbreviation=place_abbreviation)
        lp = LibraryPlace.objects.filter(library=library, place=place).first()
        if not lp:
            lp = LibraryPlace(library=library, place=place)
            lp.save()
        return lp

    def __repr__(self) -> str:
        return f"(type={self.place.type}, name={self.place.name})"


def validate_domain(domain: str) -> bool:
    matched = re.match(r"[a-z0-9-_]+\.[a-z0-9-_]{2,}", domain, flags=re.IGNORECASE)
    return matched is not None


class LibraryAllowedEmailDomains(models.Model):
    """Email domains allowed on a per library basis"""

    library = models.ForeignKey(
        Library,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="library_email_domains",
    )
    domain = LowerCharField(validators=[validate_domain], max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["library", "domain"], name="%(app_label)s_library_domain_unique"
            )
        ]


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier
    for authentication instead of username.
    """

    def create_user(
        self, email, password, library, place_abbreviation, first_name, **extra_fields
    ):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_("The email must be set"))
        if not first_name:
            raise ValueError(_("The first name must be set"))
        if not library:
            raise ValueError(_("The library must be set"))
        if not place_abbreviation:
            raise ValueError(_("The place must be set"))
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            library=library,
            first_name=first_name,
            place=Place.objects.filter(abbreviation=place_abbreviation).first(),
            **extra_fields,
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        first_name = extra_fields.get("first_name")
        if first_name is None:
            first_name = settings.DEFAULT_SUPERUSER_FIRST_NAME
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        default_library = CustomUser.get_or_create_default_library()

        return self.create_user(
            email,
            password,
            default_library,
            default_library.get_first_place(),
            first_name,
            **extra_fields,
        )


def default_library():
    """The default library for a CustomUser, must use only(id) else future migrations will break"""
    try:
        return Library.objects.order_by("id").only("id").first()
    except:
        return None


class CustomUser(AbstractUser):
    street_address_line1 = models.CharField(
        _("Street address line 1"), max_length=255, null=True, blank=False
    )
    street_address_line2 = models.CharField(
        _("Street address line 2"), max_length=255, null=True, blank=True
    )
    city = models.CharField(max_length=255, null=True, blank=False)

    place = models.ForeignKey(
        "Place",
        on_delete=models.SET_NULL,
        null=True,
        blank=False,
    )

    country_code = models.CharField(
        max_length=255, null=True, blank=False, default="US"
    )
    zip = models.CharField(
        validators=[
            RegexValidator(
                r"^([0-9A-Z]{3}(?: [A-Z0-9]{3})?)|(\d{5}(?:-\d{4})?)$",
                message="Enter a zip code in the format [XXX or XXX XXX](Canada) or [XXXXX or XXXXX-XXXX](USA)",
            )
        ],
        max_length=10,
        null=True,
    )
    library = models.ForeignKey(
        Library,
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        default=default_library,  # Default to the first library found
    )
    # AUTHENTICATION
    permanent_id = models.CharField(max_length=255, null=True)
    authorization_identifier = models.CharField(max_length=255, null=True)
    authorization_expires = models.DateField(null=True, blank=False)
    external_type = models.CharField(max_length=255, null=True, blank=False)
    email = models.EmailField(_("Email address"), null=False, blank=False, unique=True)
    over13 = models.BooleanField(
        _("    I certify that I am over 13 years old"), blank=False, default=True
    )
    username = models.CharField(
        _("username"),
        max_length=50,
        unique=False,
        null=True,
        blank=True,
        editable=False,
    )
    first_name = models.CharField(
        _("first name"), max_length=30, null=False, blank=False
    )

    # Default is true so that current and admin created users are not disabled
    email_verified = models.BooleanField(default=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self) -> str:
        return f"{self.email} ({self.first_name} {self.last_name or ''})"

    @staticmethod
    def create_card_for_library(library: Library, user, number=None):
        library_card: LibraryCard = LibraryCard()
        library_card.user = user
        library_card.library = library
        library_card.expiration_date = library_card.get_expiration_date()
        if number is None:
            CardNumber.generate_card_number(library_card)
        else:
            library_card.number = number
        return library_card

    def get_smart_name(self):
        smart_name = ""
        if self.first_name:
            smart_name = self.first_name
        if self.last_name:
            smart_name += " " + self.last_name
        return smart_name.strip()

    def library_states(self):
        return self.library.get_places()

    def library_state_name(self):
        return self.library.state_name()

    def groups_permission(self):
        """
        get group, separate by comma, and display empty string if user has no group
        """
        return (
            ",".join([g.name for g in self.groups.all()]) if self.groups.count() else ""
        )

    def library_cards(self):
        library_cards = LibraryCard.objects.filter(user=self)
        return mark_safe(
            "<br/>".join(
                [
                    "&mdash;&nbsp; "
                    + c.library.name
                    + " | "
                    + c.number
                    + c.status_str()
                    for c in library_cards
                ]
            )
            if library_cards.count()
            else ""
        )

    def nb_library_cards(self):
        library_cards = LibraryCard.objects.filter(user=self)
        return library_cards.count()

    @staticmethod
    def library_admins(library):
        return CustomUser.objects.filter(is_staff=True, library=library)

    @staticmethod
    def super_users():
        return CustomUser.objects.filter(is_superuser=True)

    def is_valid_email_domain(self) -> bool:
        """Test the validity of the users email domain"""
        email_domain = self.email.split("@")[-1]
        allowed_domains = self.library.get_allowed_email_domains()
        if allowed_domains:
            return email_domain.lower() in allowed_domains

        return True

    def clean(self) -> None:
        if not self.is_valid_email_domain():
            raise ValidationError(
                dict(
                    email=f"User must be part of allowed domains: {self.library.get_allowed_email_domains()}"
                )
            )
        return super().clean()

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.is_staff = True

        if not self.is_valid_email_domain():
            raise ValidationError(
                dict(
                    email=f"User must be part of allowed domains: {self.library.get_allowed_email_domains()}"
                )
            )

        super().save(*args, **kwargs)

    @staticmethod
    def get_or_create_default_library():
        default_library = None
        try:
            default_library = Library.objects.get(
                name=settings.DEFAULT_SUPERUSER_LIBRARY_NAME
            )  # this is the copy of the object saved in the database
        except Exception as e:
            pass

        if not default_library:
            default_library = Library.create_default_library()

        return default_library


class LibraryCard(models.Model):
    number = models.CharField(max_length=100, null=True, blank=False)
    expiration_date = models.DateTimeField(null=True, blank=True)
    library = models.ForeignKey(Library, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)
    created = models.DateTimeField(
        default=django.utils.timezone.now, verbose_name="created"
    )
    canceled_date = models.DateTimeField(null=True, blank=True)
    canceled_by_user = models.CharField(max_length=255, blank=True, null=True)

    def get_expiration_date(self):
        if (
            self.expiration_date is None
            and self.library is not None
            and self.library.card_validity_months is not None
        ):
            self.expiration_date = datetime.today() + datedelta.datedelta(
                months=+self.library.card_validity_months
            )
        return self.expiration_date

    def email(self):
        return self.user.email

    def __str__(self):
        if self.number:
            return self.number
        return self.library.name + " " + self.user.email

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        try:
            if not self.number:
                CardNumber.generate_card_number(self)

        except Exception as e:
            pass
        super().save(force_insert, force_update, using, update_fields)

    def is_expired(self):
        if self.expiration_date is None:
            return False
        return self.expiration_date < timezone.now()

    def status_str(self):
        if self.is_expired():
            return _(" | EXPIRED")
        if self.canceled_date is not None:
            return _(" | CANCELLED")
        return ""


class Place(models.Model):
    """A store of locations around the world, libraries and users should reference locations in this table
    Places are hierarchical, that means a Place may be contained within another Place.
    This is denoted by the Parent relationship.
    Eg. Texas is a state within the US, so the Place(type=state, name=Texas) will have a
    relationship parent=Place(type=country, name=United States)."""

    class Types:
        COUNTRY = "country"
        STATE = "state"
        PROVINCE = "province"
        COUNTY = "county"
        CITY = "city"

    AREA_TYPES = (
        (Types.COUNTRY, Types.COUNTRY),
        (Types.STATE, Types.STATE),
        (Types.PROVINCE, Types.PROVINCE),
        (Types.COUNTY, Types.COUNTY),
        (Types.CITY, Types.CITY),
    )

    # The external identifier from the datasource, this cannot change
    external_id = models.CharField(max_length=128, null=False, blank=False, unique=True)

    # cities and counties have blank abbreviations
    abbreviation = models.CharField(max_length=5, null=False, blank=True)

    name = models.CharField(max_length=100, null=False, blank=False)
    type = models.CharField(max_length=20, choices=AREA_TYPES)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True)

    @property
    def check_str(self) -> str:
        """Cities and Counties do not have abbreviations
        So we must check against their names
        This is a convenience function to provide the value to check against
        """
        return (
            self.abbreviation
            if self.type in (self.Types.COUNTRY, self.Types.STATE, self.Types.PROVINCE)
            else self.name
        )

    @classmethod
    def by_abbreviation(cls, abbreviation: str) -> Place:
        """Search for place with an exact match on the abbreviation"""
        return cls.objects.filter(abbreviation=abbreviation).first()

    @classmethod
    def get_states(cls, **filters) -> Place:
        """Get the states in the system, with optional query filters"""
        return cls.objects.filter(
            type__in=[cls.Types.STATE, cls.Types.PROVINCE], **filters
        ).all()

    def __str__(self) -> str:
        s = f"{self.name} | {self.type}"
        if self.parent:
            s += f" ({self.parent.check_str})"
        return s


def default_timestamp():
    """Default value for a timestamp attribute"""
    return timezone.now()


class UserConsent(models.Model):
    ## Constants and types
    class ConsentType(Enum):
        SURVEY = "SURVEY"

    class ConsentMethod(Enum):
        WEB_CARD_REQUEST = "WEB_CARD_REQUEST"

    # The wording of what the user is consenting to
    consent_text = {
        ConsentType.SURVEY: "By checking this box, I agree to receive emails for surveys, newsletters, and other promotional information from The Palace Project."
    }

    # The current version of the consent types above
    # In case the wording of a consent changes, this should be updated
    # so the version of what the user has consented to is known
    VERSIONS = {ConsentType.SURVEY: "20230408"}

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "type"], name="%(app_label)s_unique_type_user"
            )
        ]

    ## Column attributes
    user = models.ForeignKey(
        CustomUser, related_name="consents", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(default=default_timestamp)
    method = models.CharField(
        max_length=50,
        help_text="What method was used by the user for the signup.",
        choices=[(c.name, c.value) for c in ConsentMethod],
    )
    type = models.CharField(
        max_length=50,
        help_text="The type of consent.",
        choices=[(c.name, c.value) for c in ConsentType],
    )
    version = models.CharField(
        max_length=10,
        help_text="The version of the document/requirement the user consented to.",
    )

    @classmethod
    def record_consent(
        cls, user: CustomUser, typ: ConsentType, method: ConsentMethod
    ) -> UserConsent:
        """Record the user consent.
        :param user: The target user
        :param typ: The document or wording being consented to, must be part of `ConsentType`
                    A version must be available for this consent type in `UserConsent.versions`
        :param method: The method of the consent, must be part of `ConsentMethod`
        """
        if typ not in cls.ConsentType:
            raise ValueError(f"Unknown consent type {typ}")
        if typ not in cls.VERSIONS:
            raise ValueError(f"No consent version for {typ}")
        if method not in cls.ConsentMethod:
            raise ValueError(f"Unknown consent method {method}")

        # If we already have a consent simply update the data
        consent = cls.objects.filter(user=user, type=typ.value).first()
        # Else create a new consent entry
        if not consent:
            consent = cls(user=user, type=typ.value)

        # Update the content
        consent.version = cls.VERSIONS[typ]
        consent.method = method.value
        consent.timestamp = default_timestamp()
        consent.save()

        return consent

    def __str__(self) -> str:
        return f"[{self.user}]: {self.type}({self.version}) | {self.method}"
