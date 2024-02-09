from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urljoin

import requests


@dataclass
class DynamicLinksSetting:
    web_api_key: str
    domain_uri_prefix: str
    android_package_name: str
    ios_bundle_id: str


class RequestError(Exception):
    def __init__(self, response, *args: object) -> None:
        self.response = response
        super().__init__(*args)


class FirebaseDynamicLinksAPI:
    """REST interface for Firebase Dynamic Links
    https://firebase.google.com/docs/dynamic-links/rest
    """

    BASE_URL = "https://firebasedynamiclinks.googleapis.com"

    # Screen Names
    LOGIN_SCREEN = "login"

    def __init__(self, settings: DynamicLinksSetting) -> None:
        self.settings = settings

    def _request(
        self,
        method: Literal["get"] | Literal["post"],
        path: str,
        data: Any | None = None,
        json: dict | None = None,
    ) -> Any:
        """Make a REST request to the dynamic links API
        :param method: The HTTP method
        :param path: The url path component for the request
        :param data: Data body to be sent on the request
        :param json: Data body to be sent as a json
        """
        uri = urljoin(self.BASE_URL, path)
        uri = f"{uri}?key={self.settings.web_api_key}"

        response: requests.Response = requests.request(
            method, uri, data=data, json=json
        )

        if math.floor(response.status_code / 100) != 2:
            raise RequestError(response)

        if "json" in response.headers.get("Content-Type", ""):
            return response.json()

        return response.content

    def create_short_link(self, link: str) -> str | None:
        """Create a short link for an app
        :param link: The link the dynamic link shoudl redirect to
        :return: The created short link or None
        """
        path = "v1/shortLinks"
        data = {
            "dynamicLinkInfo": {
                "domainUriPrefix": self.settings.domain_uri_prefix,
                "link": link,
                "androidInfo": {
                    "androidPackageName": self.settings.android_package_name,
                },
                "iosInfo": {
                    "iosBundleId": self.settings.ios_bundle_id,
                },
            }
        }
        try:
            response: dict = self._request("post", path, json=data)
        except RequestError:
            return None
        except requests.exceptions.RequestException:
            return None

        return response["shortLink"]

    def create_signup_short_link(
        self, link_url: str, barcode: str, library_id: str
    ) -> str | None:
        """Create a short link for the library signup
        :param link_url: The url the short link should redirect to
        :param barcode: The user's library barcode
        :param library_id: The library's short name
        :return: The created short link or None
        """
        link = f"{link_url}?barcode={barcode}&libraryid={library_id}&screen={self.LOGIN_SCREEN}"
        return self.create_short_link(link)
