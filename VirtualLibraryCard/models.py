import os
from datetime import datetime

import datedelta
import django.utils.timezone
from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from localflavor.us.models import USStateField, USZipCodeField

from virtual_library_card.card_number import CardNumber
from virtual_library_card.location_utils import LocationUtils
from virtual_library_card.storage import OverwriteStorage


def value_to_link(_value, _display_label):
    if _value is not None:
        return '<a href="' + _value + '" target="_blank" >' + _display_label + "</a>"
    return ""


class Library(models.Model):
    class Meta:
        verbose_name_plural = "libraries"

    @staticmethod
    def create_default_library():
        library = Library(
            name=settings.DEFAULT_SUPERUSER_LIBRARY_NAME,
            identifier=settings.DEFAULT_SUPERUSER_LIBRARY_IDENTIFIER,
            prefix=settings.DEFAULT_SUPERUSER_LIBRARY_PREFIX,
            us_state=settings.DEFAULT_SUPERUSER_LIBRARY_STATE,
        )
        library.save()
        return library

    def generate_filename(self, filename):
        ext = f".{filename.split('.')[-1]}"  # .png
        name = "logo_%s" % self.identifier + ext
        return os.path.join("", "uploads/library/", name)

    BOOL_CHOICES = ((True, _("Descending")), (False, _("Ascending")))

    name = models.CharField(max_length=255, null=True, blank=False)
    identifier = models.CharField(max_length=255, null=True, blank=False, unique=True)
    us_state = USStateField(_("State"), blank=False)
    logo = models.ImageField(
        storage=OverwriteStorage(), upload_to=generate_filename, null=True, blank=False
    )
    phone = models.CharField(max_length=50, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    terms_conditions_url = models.CharField(max_length=255, blank=False)
    privacy_url = models.CharField(
        max_length=255, null=False, blank=False, default=settings.DEFAULT_PRIVACY_URL
    )
    social_facebook = models.CharField(max_length=255, null=True, blank=True)
    social_twitter = models.CharField(max_length=255, null=True, blank=True)
    prefix = models.CharField(max_length=10, null=True, blank=False)
    card_validity_months = models.PositiveSmallIntegerField(null=True, blank=True)
    sequence_start_number = models.IntegerField(default=0)
    sequence_end_number = models.IntegerField(null=True, blank=True)
    sequence_down = models.BooleanField(
        choices=BOOL_CHOICES, blank=False, null=False, default=False
    )

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
        return mark_safe(img_html % (logo_filename))

    def logo_thumbnail(self):
        return self.get_logo_img(self.get_logo_root_url(), self.logo_filename(), False)

    def logo_filename(self):
        if self.logo:
            return self.logo
        return "logo.png"

    def logo_header(self):
        return self.get_logo_img(self.get_logo_root_url(), self.logo_filename(), True)

    def get_logo_root_url(self):
        print("get_logo_root_url ", self.logo)
        if self.logo:
            return settings.MEDIA_URL
        print("----get_logo_root_url logo null", self.logo)
        return os.path.join(settings.STATIC_URL, "images/")

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
        print("------ saving library")
        try:
            db_library: Library = Library.objects.get(
                id=self.id
            )  # this is the copy of the object saved in the database
            if (
                db_library
                and self.sequence_start_number != db_library.sequence_start_number
            ):
                CardNumber.reset_sequence(self)

        except Exception as e:
            print("******** saving library exception", e)
        super().save(force_insert, force_update, using, update_fields)


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
            default_library.us_state,
            first_name,
            **extra_fields,
        )


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
    zip = USZipCodeField(_("Zip code"), null=False, blank=False, default="0")
    library = models.ForeignKey(
        Library, on_delete=models.PROTECT, null=False, blank=False, default=1
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

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    @staticmethod
    def create_card_for_library(library: Library, user):
        library_card: LibraryCard = LibraryCard()
        library_card.user = user
        library_card.library = library
        library_card.expiration_date = library_card.get_expiration_date()
        CardNumber.generate_card_number(library_card)
        return library_card

    def get_smart_name(self):
        smart_name = ""
        if self.first_name:
            smart_name = self.first_name
        if self.last_name:
            smart_name += " " + self.last_name
        return smart_name.strip()

    def library_state(self):
        return self.library.us_state

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

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.is_staff = True

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
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, null=True)
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
