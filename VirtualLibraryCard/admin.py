import csv
from typing import Any, Dict, List, Tuple, Union

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.http import HttpRequest, HttpResponse
from django.urls import URLPattern, URLResolver, path, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.generic.base import TemplateView
from sequences.models import Sequence

from virtual_library_card.logging import LoggingMixin
from VirtualLibraryCard.business_rules.library_card import (
    BulkUploadBadHeadersException,
    BulkUploadDuplicatesException,
    BulkUploadLibraryException,
    LibraryCardBulkUpload,
)
from VirtualLibraryCard.business_rules.user import UserRules
from VirtualLibraryCard.forms.forms import (
    CustomAdminUserChangeForm,
    CustomUserCreationForm,
    LibraryCardCreationForm,
    LibraryCardsUploadByCSVForm,
    LibraryChangeForm,
    LibraryCreationForm,
)
from VirtualLibraryCard.models import (
    CustomUser,
    Library,
    LibraryAllowedEmailDomains,
    LibraryCard,
    LibraryPlace,
    Place,
)
from VirtualLibraryCard.views.admin_email_customize import (
    AdminCustomizeWelcomeEmailView,
)


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
        "state",
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
        (
            _("Address"),
            {
                "fields": (
                    "street_address_line1",
                    "street_address_line2",
                    "city",
                    "place",
                    "zip",
                )
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
            {"fields": ("first_name", "last_name", "email", "password1", "password2")},
        ),
    )
    actions = ["export_as_csv"]

    # used by other admin forms that have search-fields on users
    # Eg. LibraryCard admin form
    search_fields = ["email"]
    ordering = ["email"]

    def state(self, obj):
        return obj.place and str(obj.place.name)

    def get_list_filter(self, request: Any) -> List[Any]:
        list_filter = super().get_list_filter(request)
        if request.user.is_superuser:
            list_filter = list_filter + ("library",)
        list_filter = list_filter + ("place",)
        return list_filter

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            if not request.user.is_superuser:
                obj.library = request.user.library
                libplace = obj.library.library_places.first()
                obj.place = libplace and libplace.place

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
        qs = super(CustomUserAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(library=request.user.library.id)


class LibraryPlacesInline(admin.StackedInline):
    model = LibraryPlace
    extra = 0
    verbose_name_plural = "Library Places"


class LibraryAllowedDomainsInline(admin.StackedInline):
    model = LibraryAllowedEmailDomains
    extra = 0
    verbose_name_plural = "Allowed Email Domains"


class LibraryAdmin(admin.ModelAdmin):
    add_form = LibraryCreationForm
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
        "sequence_down",
    ]
    list_filter = ("card_validity_months", "sequence_start_number")

    fieldsets = (
        (
            _("Identity"),
            {
                "fields": (
                    "identifier",
                    "name",
                    "patron_address_mandatory",
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
                    "sequence_start_number",
                    "sequence_end_number",
                    "sequence_down",
                )
            },
        ),
        (
            _("Configurations"),
            {
                "fields": (
                    "barcode_text",
                    "pin_text",
                    "allow_bulk_card_uploads",
                    "Customize_emails_field",
                )
            },
        ),
    )
    readonly_fields = ["logo_thumbnail"]

    actions = ["export_as_csv"]

    inlines = [
        LibraryPlacesInline,
        LibraryAllowedDomainsInline,
    ]

    @admin.decorators.display(description="US States")
    def get_place_abbrs(self, obj):
        """Display the state abbreviations on the list page"""
        return [lp.place.abbreviation for lp in obj.library_places.all()]

    def get_queryset(self, request):
        qs = super(LibraryAdmin, self).get_queryset(request)
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

    def get_list_filter(self, request: Any) -> Tuple[Any]:
        return (
            ("library", "expiration_date")
            if request.user.is_superuser
            else ("expiration_date",)
        )

    def get_queryset(self, request):
        qs = super(LibraryCardAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(library=request.user.library.id)

    def export_as_csv(self, request, queryset):
        return export_list_as_csv(self, request, queryset)

    export_as_csv.short_description = _("Export selected library cards")


class CustomSequenceAdmin(admin.ModelAdmin):
    list_display = ["name", "last"]
    ordering = ["name"]
    readonly_fields = ["name", "last"]
    list_display_links = ()
    model = Sequence

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}


def export_list_as_csv(self, request, queryset):
    meta = self.model._meta
    field_names = [field.name for field in meta.fields]
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename={}.csv".format(meta)
    writer = csv.writer(response)

    writer.writerow(field_names)
    for obj in queryset:
        row = writer.writerow([getattr(obj, field) for field in field_names])

    return response


class LibraryCardsUploadCSV(TemplateView):
    """The template view that displays the bulk CSV form on the admin panel"""

    template_name: str = "library_card/upload_by_csv.html"

    http_method_names: List[str] = ["get", "post"]

    def _get_columns_ctx(self) -> Dict[str, Any]:
        return dict(
            required_columns=", ".join(LibraryCardBulkUpload.REQUIRED_CSV_HEADERS),
            optional_columns=", ".join(LibraryCardBulkUpload.OPTIONAL_CSV_HEADERS),
        )

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = LibraryCardsUploadByCSVForm()
        ctx.update(self._get_columns_ctx())
        return ctx

    def post(self, request: HttpRequest) -> HttpResponse:
        """The form post submit"""
        form = LibraryCardsUploadByCSVForm(data=request.POST, files=request.FILES)
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


class VLCAdminSite(admin.AdminSite):
    """The admin site configuration"""

    def get_urls(self) -> List[Union[URLResolver, URLPattern]]:
        urls = super().get_urls()
        urls = [
            path("librarycard/upload_by_csv", LibraryCardsUploadCSV.as_view()),
            path(
                "VirtualLibraryCard/library/<id>/welcome_email/update",
                AdminCustomizeWelcomeEmailView.as_view(),
            ),
        ] + urls
        return urls


admin_site = VLCAdminSite()
admin_site.enable_nav_sidebar = False
admin_site.register(CustomUser, CustomUserAdmin)
admin_site.register(Library, LibraryAdmin)
admin_site.register(LibraryCard, LibraryCardAdmin)
admin_site.register(Sequence, CustomSequenceAdmin)
admin_site.register(Place, admin.ModelAdmin)
