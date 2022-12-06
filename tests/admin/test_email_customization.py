import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from tests.base import BaseUnitTest
from virtuallibrarycard.views.admin_email_customize import (
    AdminCustomizeWelcomeEmailView,
)


class TestEmailCustomization(BaseUnitTest):
    def setup_method(self, request):
        super().setup_method(request)
        self.library = self.create_library()
        self.view = AdminCustomizeWelcomeEmailView()

    def test_get_context_data(self):
        request = RequestFactory().get("/")
        self.view.setup(request, id=self.library.id)
        ctx = self.view.get_context_data()

        # The right library name is set
        assert f"Thank you for joining {self.library.name}." in ctx["email_str"]
        # Replaceable text shows up in the template
        assert "[[CUSTOM_TOP_TEXT]]" in ctx["email_str"]
        assert "[[CUSTOM_BOTTOM_TEXT]]" in ctx["email_str"]

    def test_get_initial(self):
        request = RequestFactory().get("/")
        self.view.setup(request, id=self.library.id)
        self.library.customization.welcome_email_bottom_text = "bottom"
        self.library.customization.welcome_email_top_text = "top"
        self.library.customization.save()
        initial = self.view.get_initial()

        assert initial == {"top_text": "top", "bottom_text": "bottom"}

    def test_form_valid(self):
        request = RequestFactory().post(
            "/",
            data=dict(top_text="top text&nbsp;", bottom_text="bottom text<br/>"),
        )
        self.view.setup(request, id=self.library.id)
        response = self.view.post(request)

        self.library.refresh_from_db()
        assert response.status_code == 200
        assert self.library.customization.welcome_email_top_text == "top text&nbsp;"
        assert (
            self.library.customization.welcome_email_bottom_text == "bottom text<br/>"
        )

    def test_permissions(self):
        factory = RequestFactory()
        get_request = factory.get("/")

        # superusers allowed
        superuser = self.create_user(self._default_library, is_superuser=True)
        get_request.user = superuser
        self.view.setup(get_request, id=self.library.id)
        response = self.view.dispatch(get_request)
        assert response.status_code == 200

        # regular users are not allowed
        get_request.user = self._default_user
        self.view.setup(get_request, id=self.library.id)
        with pytest.raises(PermissionDenied):
            self.view.dispatch(get_request)

        # Staff members not of the library may not access the page
        staff = self.create_user(self._default_library, is_staff=True)
        get_request.user = staff
        self.view.setup(get_request, id=self.library.id)
        with pytest.raises(PermissionDenied):
            self.view.dispatch(get_request)

        # staff members of the library can access the page
        staff.library = self.library
        self.view.setup(get_request, id=self.library.id)
        response = self.view.dispatch(get_request)
        assert response.status_code == 200
