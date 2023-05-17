from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from requests import Response

from tests.base import BaseUnitTest
from virtual_library_card.api.dynamic_links import (
    DynamicLinksSetting,
    FirebaseDynamicLinksAPI,
    RequestError,
)


class TestFirebaseDynamicLinksAPI(BaseUnitTest):
    def _response(self, status_code, headers=None, json=None, **kwargs):
        m = MagicMock(spec=Response)
        m.status_code = status_code
        m.headers = headers or {}
        m.json.return_value = json
        for k, v in kwargs.items():
            setattr(m, k, v)
        return m

    def test__request(self):
        """Test the basic request making method"""
        dl_settings = DynamicLinksSetting(**settings.DYNAMIC_LINKS)
        api = FirebaseDynamicLinksAPI(dl_settings)

        with patch("virtual_library_card.api.dynamic_links.requests") as requests:
            requests.request.return_value = self._response(200, content="test-response")
            resp = api._request("post", "test-path", data="123", json=dict(test=True))
            requests.request.assert_called_once()
            requests.request.assert_called_with(
                "post",
                f"{api.BASE_URL}/test-path?key={dl_settings.web_api_key}",
                data="123",
                json=dict(test=True),
            )
            assert resp == "test-response"

            with pytest.raises(RequestError) as raised:
                requests.request.return_value = self._response(
                    300, content="test-response"
                )
                api._request("post", "test-path")
            assert raised.value.response.content == "test-response"

            requests.request.return_value = self._response(
                200,
                json="test-json",
                content="test-content",
                headers={"Content-Type": "application/json"},
            )
            resp = api._request("post", "test-path")
            assert resp == "test-json"

    def test_create_short_link(self):
        dl_settings = DynamicLinksSetting(**settings.DYNAMIC_LINKS)
        api = FirebaseDynamicLinksAPI(dl_settings)
        api._request = MagicMock(return_value=dict(shortLink="short-link"))

        resp_link = api.create_short_link("link")
        body = {
            "domainUriPrefix": dl_settings.domain_uri_prefix,
            "link": "link",
            "androidInfo": {"androidPackageName": dl_settings.android_package_name},
            "iosInfo": {"iosBundleId": dl_settings.ios_bundle_id},
        }
        assert resp_link == "short-link"
        assert api._request.call_count == 1
        api._request.assert_called_with(
            "post", "v1/shortLinks", json=dict(dynamicLinkInfo=body)
        )

    def test_create_signup_short_link(self):
        dl_settings = DynamicLinksSetting(**settings.DYNAMIC_LINKS)
        api = FirebaseDynamicLinksAPI(dl_settings)
        api.create_short_link = MagicMock(return_value="short-link")

        resp = api.create_signup_short_link("link-url", "barcode", "library-id")
        assert resp == "short-link"
        api.create_short_link.assert_called_once_with(
            f"link-url?barcode=barcode&libraryid=library-id&screen=login"
        )
