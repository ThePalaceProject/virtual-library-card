"""virtual_library_card URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from virtuallibrarycard.admin import admin_site
from virtuallibrarycard.views import (
    CustomLoginView,
    LibraryCardDeleteView,
    PasswordChangeDoneView,
    PinTestPOSTViewSet,
    PinTestViewSet,
    PlaceSearchAheadView,
    ProfileView,
    TemplateView,
    UserLibraryCardViewSet,
    debug_templates,
    views_library_card,
    views_password,
    views_profile,
)
from virtuallibrarycard.views.views_verification import (
    EmailVerificationErrorView,
    EmailVerificationResendToken,
    EmailVerificationTokenView,
)
from virtuallibrarycard.views.views_version import VersionView

urlpatterns = []

if settings.HAS_API:
    api_patterns = [
        # API reference: https://documentation.iii.com/sierrahelp/Content/sril/sril_patronapi.html
        # / PATRONAPI / {barcode} / {pin} / dump
        path("<number>/dump", UserLibraryCardViewSet.as_view()),
        # / PATRONAPI / {barcode} / {pin} / pintest
        path("<number>/<pin>/pintest", PinTestViewSet.as_view()),
        # / PATRONAPI / pintest
        path("pintest", PinTestPOSTViewSet.as_view()),
    ]

    urlpatterns += [
        # We provide the API at two different URLS /api and /PATRONAPI
        # This is because we were using /api as an endpoint, but some consumers of the API (overdrive)
        # only support this API if it is at the /PATRONAPI endpoint.
        path("api/", include(api_patterns)),
        path("PATRONAPI/", include(api_patterns)),
    ]

if settings.HAS_WEBSITE:
    urlpatterns += [
        # HOME
        path("", views_profile.ProfileView.as_view()),
        # ADMIN
        path("admin/", admin_site.urls),
        path("place/search", PlaceSearchAheadView.as_view(), name="place_typeahead"),
        path("accounts/", include("django.contrib.auth.urls")),
        # APPLY FOR LIBRARY CARD
        path(
            "account/library_card_request/",
            views_library_card.LibraryCardRequestView.as_view(),
            name="library_card_request",
        ),
        path(
            "account/library_card_request/<identifier>/",
            views_library_card.LibraryCardRequestView.as_view(),
        ),
        path(
            "account/library_card_signup/<identifier>/",
            views_library_card.CardSignupView.as_view(),
        ),
        path(
            "account/library_card_request_success/<email>/",
            views_library_card.LibraryCardRequestSuccessView.as_view(),
            name="library_card_request_success",
        ),
        path(
            "account/library_card_request/denied_country",
            TemplateView.as_view(
                template_name="library_card" "/library_card_request_denied_country.html"
            ),
        ),
        path(
            "account/library_card_request/geolocation_denied",
            TemplateView.as_view(
                template_name="library_card" "/library_card_request_denied_geoloc.html"
            ),
        ),
        path(
            "account/library_card_request/denied/<state_name>",
            TemplateView.as_view(
                template_name="library_card" "/library_card_request_denied.html"
            ),
        ),
        # LOGIN
        path("accounts/login/<identifier>/", CustomLoginView.as_view(), name="login"),
        # RESET PASSWORD
        path(
            "account/reset-password/",
            views_password.CustomResetPasswordView.as_view(),
            name="reset-password",
        ),
        path(
            "account/reset-password/<identifier>/",
            views_password.CustomResetPasswordView.as_view(),
            name="reset-password",
        ),
        # PROFILE
        path("account/edit/<first_name>/", views_profile.ProfileEditView.as_view()),
        path("account/delete/<first_name>/", views_profile.ProfileDeleteView.as_view()),
        path(
            "account/delete/<first_name>/delete_profile_success",
            TemplateView.as_view(
                template_name="accounts" "/delete_profile_success.html"
            ),
        ),
        path("accounts/profile/", ProfileView.as_view(), name="profile"),
        path("account/profile/<first_name>/", ProfileView.as_view(), name="profile"),
        path(
            "account/profile/<delete_cards>/<success>/",
            ProfileView.as_view(),
            name="card_deleted_success",
            kwargs={"delete_cards": True, "success": True},
        ),
        path(
            "account/delete/<first_name>/cards/",
            views_library_card.LibraryCardsView.as_view(),
        ),
        path("account/library_cards/cancel/<number>", LibraryCardDeleteView.as_view()),
        # MANAGE PASSWORD
        path(
            "account/change-password/<first_name>/",
            views_password.CustomPasswordChangeView.as_view(),
        ),
        path(
            "account/change-password/<first_name>/password_change_done/",
            PasswordChangeDoneView.as_view(),
            name="password_change_done",
        ),
        path(
            "verify/email",
            EmailVerificationTokenView.as_view(),
            name="email_token_verify",
        ),
        path(
            "verify/email/resend",
            EmailVerificationResendToken.as_view(),
            name="email_token_resend",
        ),
        path(
            "verify/email/error",
            EmailVerificationErrorView.as_view(),
            name="email_token_error",
        ),
    ]

    if settings.DEBUG:
        urlpatterns += [
            path(
                "debug/template/<path:template_path>",
                debug_templates,
                name="debug_templates",
            )
        ]
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Controller that returns information about the version of the deployed app
urlpatterns += [
    path("version.json", VersionView.as_view()),
]

handler404 = "virtuallibrarycard.views.handler404"
handler400 = "virtuallibrarycard.views.handler400"
handler500 = "virtuallibrarycard.views.handler500"
