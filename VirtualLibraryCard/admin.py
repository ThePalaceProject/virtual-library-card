import csv

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse
from django.utils.translation import gettext as _
from sequences.models import Sequence

from VirtualLibraryCard.forms.forms import (
    CustomAdminUserChangeForm,
    CustomUserCreationForm,
    LibraryCardCreationForm,
    LibraryChangeForm,
    LibraryCreationForm,
)
from VirtualLibraryCard.models import CustomUser, Library, LibraryCard, LibraryStates


class CustomUserAdmin(UserAdmin):
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
        "us_state",
        "groups_permission",
        "nb_library_cards",
    ]
    list_display_links = ("first_name", "last_name", "email")
    list_filter = UserAdmin.list_filter + ("library", "us_state")
    fieldsets = (
        (
            _("Personal Info"),
            {"fields": ("first_name", "last_name", "email", "over13")},
        ),
        (
            _("Address"),
            {
                "fields": (
                    "street_address_line1",
                    "street_address_line2",
                    "city",
                    "us_state",
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

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            if not request.user.is_superuser:
                obj.library = request.user.library
                obj.us_state = obj.library.get_first_us_state()

        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        ro_fields = ["library_cards"]
        if request.user and not request.user.is_superuser:
            ro_fields.append("library")
        if (
            obj and obj.us_state
        ):  # This is the case when obj is already created i.e. it's an edit
            ro_fields.append("us_state")

        return ro_fields

    def export_as_csv(self, request, queryset):
        return export_list_as_csv(self, request, queryset)

    export_as_csv.short_description = _("Export selected users")

    def get_queryset(self, request):
        qs = super(CustomUserAdmin, self).get_queryset(request)
        print(request.user.is_superuser, "request.user.is_superuser")
        if request.user.is_superuser:
            return qs
        return qs.filter(library=request.user.library.id)


class LibraryStatesInline(admin.StackedInline):
    model = LibraryStates
    extra = 0
    verbose_name_plural = "Library States"


class LibraryAdmin(admin.ModelAdmin):
    add_form = LibraryCreationForm
    form = LibraryChangeForm
    model = Library

    list_display = [
        "logo_thumbnail",
        "name",
        "identifier",
        "get_us_states",
        "phone",
        "email",
        "terms_conditions_link",
        "social_links",
        "card_validity_months",
        "sequence_down",
    ]
    list_filter = ("card_validity_months", "sequence_start_number")

    inlines = [LibraryStatesInline]

    fieldsets = (
        (_("Identity"), {"fields": ("identifier", "name", "logo")}),
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
                    "sequence_start_number",
                    "sequence_end_number",
                    "sequence_down",
                )
            },
        ),
    )
    readonly_fields = ["logo_thumbnail"]

    actions = ["export_as_csv"]

    def get_us_states(self, obj):
        return obj.get_us_states()

    get_us_states.short_description = "US States"

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
    add_form = LibraryCardCreationForm
    list_display = [
        "number",
        "user",
        "email",
        "expiration_date",
        "canceled_date",
        "canceled_by_user",
        "library",
    ]
    list_filter = ("library", "expiration_date")
    actions = ["export_as_csv"]
    readonly_fields = (
        "number",
        "user",
        "canceled_date",
        "canceled_by_user",
        "library",
        "created",
    )

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
            return ["number", "canceled_date", "canceled_by_user", "created"]

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


admin.site.enable_nav_sidebar = False
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Library, LibraryAdmin)
admin.site.register(LibraryCard, LibraryCardAdmin)
admin.site.unregister(Sequence)
admin.site.register(Sequence, CustomSequenceAdmin)
