import os
import re
from datetime import datetime
from typing import List

import datedelta
import django.utils.timezone
from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import models
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from localflavor.us.models import USStateField, USZipCodeField

from virtual_library_card.card_number import CardNumber
from virtual_library_card.location_utils import LocationUtils
from virtual_library_card.logging import log


def value_to_link(_value, _display_label):
    if _value is not None:
        return '<a href="' + _value + '" target="_blank" >' + _display_label + "</a>"
    return ""


class LowerCharField(models.CharField):
    """CharField like column, but forces values to lowercase before saving to the DB"""

    def get_prep_value(self, value: str) -> str:
        value = value.lower()
        return super().get_prep_value(value)


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

        ls = LibraryStates(
            library=library, us_state=settings.DEFAULT_SUPERUSER_LIBRARY_STATE
        )
        ls.save()

        return library

    def generate_filename(self, filename):
        ext = f".{filename.split('.')[-1]}"  # .png
        name = "logo_%s" % self.identifier + ext
        return os.path.join("", "uploads/library/", name)

    BOOL_CHOICES = ((True, _("Descending")), (False, _("Ascending")))

    name = models.CharField(max_length=255, null=True, blank=False)
    identifier = models.CharField(max_length=255, null=True, blank=False, unique=True)

    ## Deprecated - do not use this field, use only the LibraryState association
    us_state = USStateField(_("State"), blank=False)
    us_state.system_check_deprecated_details = dict(
        msg="Library.us_state is a deprecated field",
        hint="Use LibraryState associations only",
        id="fields.us_state_001",
    )
    ######

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
        choices=((True, _("Yes")), (False, _("No"))),
        blank=False,
        default=True,
        verbose_name="Require Patron Address",
    )
    allow_all_us_states = models.BooleanField(
        choices=((True, _("Yes")), (False, _("No"))),
        blank=False,
        default=False,
        verbose_name="Allow All US States",
    )
    barcode_text = models.CharField(
        max_length=255, default="barcode", verbose_name="Barcode Text"
    )
    pin_text = models.CharField(max_length=255, default="pin", verbose_name="Pin Text")
    age_verification_mandatory = models.BooleanField(
        choices=((True, _("Yes")), (False, _("No"))),
        blank=False,
        default=True,
        verbose_name="Require Patron Age Verification",
    )
    allow_bulk_card_uploads = models.BooleanField(
        choices=((True, _("Yes")), (False, _("No"))),
        blank=False,
        default=False,
        verbose_name="Allow Bulk Upload For Library Cards",
    )

    def get_us_states(self):
        return [ls.us_state for ls in self.library_states.order_by("id").all()]

    def get_first_us_state(self):
        return self.get_us_states()[0]

    def get_logo_img(self, root_url, logo_filename, header):
        img_html = (
            '<img  alt="'
            + self.name
            + ' logo" aria-label="'
            + self.name
            + ' logo"  src="'
            + root_url
            + '%s" '
        )
        if header:
            img_html += ' class="logo"'
        else:
            img_html += ' width="100px"'
        img_html += " />"

        file_url = (
            logo_filename if root_url else default_storage.url(str(logo_filename))
        )
        return mark_safe(img_html % (file_url))

    def logo_thumbnail(self):
        return self.get_logo_img(self.get_logo_root_url(), self.logo_filename(), False)

    def logo_filename(self):
        if self.logo:
            return self.logo
        return "logo.png"

    def logo_header(self):
        return self.get_logo_img(self.get_logo_root_url(), self.logo_filename(), True)

    def get_logo_root_url(self):
        if not self.logo:
            return os.path.join(settings.STATIC_URL, "images/")
        return ""

    def state_name(self):
        return LocationUtils.get_library_state_name(self)

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

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        try:
            db_library: Library = Library.objects.get(
                id=self.id
            )  # this is the copy of the object saved in the database
            if (
                db_library
                and self.sequence_start_number != db_library.sequence_start_number
            ):
                CardNumber.reset_sequence(self)
        except Library.DoesNotExist:
            pass
        except Exception as e:
            log.exception("******** saving library exception")
        super().save(force_insert, force_update, using, update_fields)

    def get_allowed_email_domains(self) -> List[str]:
        return [e.domain for e in self.library_email_domains.all()]


class LibraryStates(models.Model):
    """Library to state relations"""

    library = models.ForeignKey(
        Library,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="library_states",
    )
    us_state = USStateField(_("State"), blank=False)


def validate_domain(domain: str) -> bool:
    matched = re.match("[a-z0-9-_]+\.[a-z0-9-_]{2,}", domain, flags=re.IGNORECASE)
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
        self, email, password, library, us_state, first_name, **extra_fields
    ):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        if not first_name:
            raise ValueError(_("The First name must be set"))
        if not library:
            raise ValueError(_("The Library must be set"))
        if not us_state:
            raise ValueError(_("The State must be set"))
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            library=library,
            us_state=us_state,
            first_name=first_name,
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
            default_library.get_first_us_state(),
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
    us_state = USStateField(_("State"), null=False, blank=False)
    country_code = models.CharField(
        max_length=255, null=True, blank=False, default="US"
    )
    zip = USZipCodeField(_("Zip code"), null=True, blank=False)
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
        return self.library.get_us_states()

    def library_state_name(self):
        return LocationUtils.get_library_state_name(self.library)

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

        super(CustomUser, self).save(*args, **kwargs)

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
