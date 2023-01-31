import pytest
from django.core.handlers.wsgi import WSGIRequest
from rest_framework.test import APIRequestFactory

import virtual_library_card
from virtuallibrarycard.views.views_version import VersionView


class TestVersionView:
    @pytest.fixture
    def view(self):
        request: WSGIRequest = APIRequestFactory().get("/version.json")
        view = VersionView.as_view()
        return lambda: view(request)

    def test_get_method_no_version(self, view):
        response = view()
        assert response.content_type == "application/json"
        assert response.status_code == 200
        assert response.data == {"version": None, "commit": None, "branch": None}

    def test_get_method(self, view, monkeypatch):
        version = "1.x.x"
        branch = "feature/add-version"
        commit = "1337"
        monkeypatch.setattr(virtual_library_card, "__version__", version)
        monkeypatch.setattr(virtual_library_card, "__branch__", branch)
        monkeypatch.setattr(virtual_library_card, "__commit__", commit)
        response = view()
        assert response.data == {"version": version, "commit": commit, "branch": branch}
