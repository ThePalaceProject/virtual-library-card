from __future__ import annotations

import csv
import datetime
from io import StringIO
from typing import Any

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
    StreamingHttpResponse,
)
from django.urls import URLPattern, URLResolver, path, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.generic.base import TemplateView

from virtual_library_card.logging import LoggingMixin
from virtuallibrarycard.business_rules.library_card import (
    BulkUploadBadHeadersException,
    BulkUploadDuplicatesException,
    BulkUploadLibraryException,
    LibraryCardBulkUpload,
)
from virtuallibrarycard.business_rules.user import UserRules
from virtuallibrarycard.forms.forms import (
    CustomAdminUserChangeForm,
    CustomPlaceChangeForm,
    CustomUserCreationForm,
    LibraryCardCreationForm,
    LibraryCardsUploadByCSVForm,
    LibraryChangeForm,
)
from virtuallibrarycard.models import (
    CustomUser,
    Library,
    LibraryAllowedEmailDomains,
    LibraryCard,
    Place,
    UserConsent,
)
from virtuallibrarycard.views.admin_email_customize import (
    AdminCustomizeWelcomeEmailView,
)


class UserConsentInline(admin.StackedInline):
    model = UserConsent
    extra = 0
    verbose_name = "User Consent"

    def has_add_permission(self, request: HttpRequest, obj) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: Any | None = ...
    ) -> bool:
        return False


class CustomUserAdmin(LoggingMixin, UserAdmin):
    add_form_template = "admin/user_add_form.html"
    add_form = CustomUserCreationForm
    form = CustomAdminUserChangeForm
    model = CustomUser
    list_display = [
        "first_name",
        "last_name",
        "email",
        "is_superuser",
        "is_staff",
        "is_active",
        "library",
        "authorization_expires",
        "groups_permission",
        "nb_library_cards",
    ]
    list_display_links = ("first_name", "last_name", "email")
    fieldsets = (
        (
            _("Personal Info"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "over13",
                    "email_verified",
                )
            },
        ),
        (
            _("Password"),
            {
                "fields": ("password",),
                "description": "This password/PIN is used to login to this website and is the pin associated with your library card in the Palace app.",
            },
        ),
        (_("Library Info"), {"fields": ("library", "library_cards")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "password1",
                    "password2",
                    "library",
                )
            },
        ),
    )
    actions = ["export_as_csv"]

    # used by other admin forms that have search-fields on users
    # Eg. LibraryCard admin form
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["email"]

    def get_inlines(self, request, obj):
        # Only want to display consents when we are editing a current user
        if obj:
            return [UserConsentInline]
        return []

    def get_list_filter(self, request: Any) -> list[Any]:
        list_filter = super().get_list_filter(request)
        if request.user.is_superuser:
            list_filter = list_filter + ("library",)
        return list_filter

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            if not request.user.is_superuser:
                obj.library = request.user.library

        super().save_model(request, obj, form, change)

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        """Use this method to modify any "related" objects. Eg: permissions"""
        super().save_related(request, form, formsets, change)
        user = form.instance
        # We only change the permissions if the status of the user was changed
        # ie. if the staff or superuser checkboxes were changed
        if user and {"is_staff", "is_superuser"}.intersection(form.changed_data):
            UserRules.drop_permissions(user)
            UserRules.ensure_permissions(user)

    def save_form(self, request: Any, form: Any, change: Any):
        # This will call form.save()
        user: CustomUser = super().save_form(request, form, change)
        if not user:
            return

        if (
            isinstance(form, CustomAdminUserChangeForm)
            and form.created_library_card is not None
        ):
            card = form.created_library_card
            name = f"admin:{LibraryCard._meta.app_label}_{LibraryCard._meta.model_name}_change"
            change_route = reverse(name, kwargs={"object_id": card.id})
            messages.info(
                request,
                mark_safe(
                    f"Created Library Card <a href='{change_route}'>{card.number}</a>"
                ),
            )

        return user

    def get_readonly_fields(self, request, obj=None):
        ro_fields = ["library_cards"]
        if request.user and not request.user.is_superuser:
            ro_fields.append("library")
            ro_fields.append("is_superuser")

        return ro_fields

    def export_as_csv(self, request, queryset):
        return export_list_as_csv(self, request, queryset)

    export_as_csv.short_description = _("Export selected users")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(library=request.user.library.id)


class LibraryAllowedDomainsInline(admin.StackedInline):
    model = LibraryAllowedEmailDomains
    extra = 0
    verbose_name_plural = "Allowed Email Domains"


class LibraryAdmin(admin.ModelAdmin):
    form = LibraryChangeForm
    model = Library

    list_display = [
        "logo_thumbnail",
        "name",
        "identifier",
        "get_place_abbrs",
        "phone",
        "email",
        "terms_conditions_link",
        "social_links",
        "card_validity_months",
    ]
    list_filter = ("card_validity_months",)

    fieldsets = (
        (
            _("Identity"),
            {
                "fields": (
                    "identifier",
                    "name",
                    "age_verification_mandatory",
                    "logo",
                )
            },
        ),
        (_("Contact"), {"fields": ("phone", "email")}),
        (
            _("Links"),
            {
                "fields": (
                    "privacy_url",
                    "terms_conditions_url",
                    "social_facebook",
                    "social_twitter",
                )
            },
        ),
        (
            _("Cards Config"),
            {
                "fields": (
                    "card_validity_months",
                    "prefix",
                    "bulk_upload_prefix",
                )
            },
        ),
        (
            _("Configurations"),
            {
                "fields": (
                    "has_survey_consent",
                    "barcode_text",
                    "pin_text",
                    "allow_bulk_card_uploads",
                    "Customize_emails_field",
                )
            },
        ),
        (_("Places"), {"fields": ("places_filter",)}),
    )
    readonly_fields = ["logo_thumbnail"]

    actions = ["export_as_csv"]

    inlines = [
        LibraryAllowedDomainsInline,
    ]

    @admin.decorators.display(description="US States")
    def get_place_abbrs(self, obj):
        """Display the state abbreviations on the list page"""
        return [lp.place.abbreviation for lp in obj.library_places.all()]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(id=request.user.library.id)

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return []
        else:
            return ["identifier"]

    def export_as_csv(self, request, queryset):
        return export_list_as_csv(self, request, queryset)

    export_as_csv.short_description = _("Export selected libraries")


class LibraryCardAdmin(admin.ModelAdmin):
    model = LibraryCard
    form = LibraryCardCreationForm
    list_display = [
        "number",
        "user",
        "email",
        "expiration_date",
        "canceled_date",
        "canceled_by_user",
        "library",
    ]

    actions = ["export_as_csv"]
    readonly_fields = (
        "number",
        "user",
        "canceled_date",
        "canceled_by_user",
        "library",
        "created",
    )
    autocomplete_fields = ["user"]

    def get_readonly_fields(self, request, obj=None):
        if obj:  # This is the case when obj is already created i.e. it's an edit
            return [
                "number",
                "user",
                "canceled_date",
                "canceled_by_user",
                "library",
                "created",
            ]
        else:
            return ["canceled_date", "canceled_by_user", "created"]

    def get_list_filter(self, request: Any) -> tuple[Any]:
        return (
            ("library", "expiration_date")
            if request.user.is_superuser
            else ("expiration_date",)
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(library=request.user.library.id)

    def export_as_csv(self, request, queryset):
        return export_list_as_csv(self, request, queryset)

    export_as_csv.short_description = _("Export selected library cards")

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict[str, bool] | None = {},
    ) -> HttpResponse:
        """Overridden to add the password reset url extra context"""
        user = LibraryCard.objects.get(id=object_id).user
        if user:
            extra_context["reset_password_url"] = (
                f"../../../customuser/{user.id}/password"
            )
        return super().change_view(request, object_id, form_url, extra_context)


def export_list_as_csv(self, request, queryset):
    meta = self.model._meta
    field_names = [field.name for field in meta.fields]
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={meta}.csv"
    writer = csv.writer(response)

    writer.writerow(field_names)
    for obj in queryset:
        row = writer.writerow([getattr(obj, field) for field in field_names])

    return response


class LibraryCardsUploadCSV(PermissionRequiredMixin, TemplateView):
    """The template view that displays the bulk CSV form on the admin panel"""

    template_name: str = "library_card/upload_by_csv.html"

    http_method_names: list[str] = ["get", "post"]

    def has_permission(self) -> bool:
        """Only allow superusers or staff members that are of the same library"""
        user = self.request.user
        if not (user.is_staff or user.is_superuser):
            return False
        # In a GET request, anybody with change permission is allowed
        if self.request.method == "GET":
            return True
        # superusers are exempt
        elif user.is_superuser:
            return True
        # A form submit needs the user to belong to the library being modified.
        elif self.request.method == "POST" and user.is_staff:
            return user.library.id == int(self.request.POST.get("library", 0))

        return False

    def _get_columns_ctx(self) -> dict[str, Any]:
        return dict(
            required_columns=", ".join(LibraryCardBulkUpload.REQUIRED_CSV_HEADERS),
            optional_columns=", ".join(LibraryCardBulkUpload.OPTIONAL_CSV_HEADERS),
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = LibraryCardsUploadByCSVForm(self.request.user)
        ctx.update(self._get_columns_ctx())
        return ctx

    def post(self, request: HttpRequest) -> HttpResponse:
        """The form post submit"""
        form = LibraryCardsUploadByCSVForm(
            self.request.user, data=request.POST, files=request.FILES
        )
        if form.is_valid():
            try:
                library: Library = Library.objects.get(
                    id=int(form.cleaned_data["library"])
                )
                LibraryCardBulkUpload.bulk_upload_csv(
                    library,
                    form.files["csv_file"],
                    admin_user=request.user,
                    _async=True,
                )
            except BulkUploadBadHeadersException as e:
                form.add_error("csv_file", str(e))
            except BulkUploadDuplicatesException as e:
                fstr = f"Duplicate values present in the file: emails: {e.duplicates['emails']}, ids: {e.duplicates['ids']}"
                form.add_error("csv_file", fstr)
            except BulkUploadLibraryException as e:
                form.add_error("library", str(e))
            else:
                messages.add_message(
                    request, messages.SUCCESS, f"User upload has been initiated."
                )

        ctx = self.get_context_data()
        ctx["form"] = form
        return self.render_to_response(ctx)


class PlaceAdmin(admin.ModelAdmin):
    model = Place
    list_display = ["name", "type", "parent"]
    ordering = ["name"]
    list_filter = ["type"]
    search_fields = ["name", "abbreviation__exact", "parent__name"]
    form = CustomPlaceChangeForm

    class Media:
        js = ["js/admin/place.js"]


def export_users_by_consent(request: HttpRequest):
    """Export users by consent type in a csv format.
    The method expects a GET parameter 'type'.
    """
    # Only staff and admin users
    if not request.user.is_staff:
        return HttpResponseForbidden()

    consent_type = request.GET["type"]
    content = StringIO()
    consents = UserConsent.objects.filter(type=consent_type).all()
    headers = ["name", "email", "type", "method", "version", "time"]
    csv_content = csv.DictWriter(content, fieldnames=headers)
    csv_content.writeheader()

    for consent in consents:
        item = dict(
            name=consent.user.get_full_name(),
            email=consent.user.email,
            type=consent.type,
            method=consent.method,
            version=consent.version,
            time=consent.timestamp,
        )
        csv_content.writerow(item)

    content.seek(0)
    response = StreamingHttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = (
        f"attachment; filename=consented_users_{consent_type}_{datetime.datetime.now()}.csv"
    )
    return response


class VLCAdminSite(admin.AdminSite):
    """The admin site configuration"""

    def get_urls(self) -> list[URLResolver | URLPattern]:
        urls = super().get_urls()
        urls = [
            path("librarycard/upload_by_csv", LibraryCardsUploadCSV.as_view()),
            path(
                "virtuallibrarycard/library/<id>/welcome_email/update",
                AdminCustomizeWelcomeEmailView.as_view(),
            ),
            path("customuser/export_by_consent", export_users_by_consent),
        ] + urls
        return urls


admin_site = VLCAdminSite()
admin_site.enable_nav_sidebar = False
admin_site.register(CustomUser, CustomUserAdmin)
admin_site.register(Library, LibraryAdmin)
admin_site.register(LibraryCard, LibraryCardAdmin)
admin_site.register(Place, PlaceAdmin)
