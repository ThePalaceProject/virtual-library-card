"""
WSGI config for virtual_library_card project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

from virtual_library_card.logging import log

UWSGI_PRESENT = True
try:
    import uwsgi
except ImportError:
    UWSGI_PRESENT = False

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "virtual_library_card.settings.prod")

django_app = get_wsgi_application()


class CensorUriException(Exception):
    pass


def censor_password_from_pintest_uri(uri):
    # Pintest uri is in the form of /{api,PATRONAPI}/<card_number>/<password>/pintest
    if "pintest" not in uri:
        return uri

    couldnt_censor_uri_exception = CensorUriException(
        f"Couldn't censor pintest uri - {uri}"
    )

    split_uri = uri.split("/")

    # split_uri should be ["", "{api,PATRONAPI}", "<card_number>", "<password>", "pintest"]
    # It contains empty string on index 0 due to prefix slash in the uri
    password_index = 3

    if len(split_uri) != 5:
        raise couldnt_censor_uri_exception

    if split_uri[1] not in {"api", "PATRONAPI"}:
        raise couldnt_censor_uri_exception

    if split_uri[-1] != "pintest":
        raise couldnt_censor_uri_exception

    split_uri[password_index] = "***"

    censored_uri = "/".join(split_uri)

    return censored_uri


def uwsgi_app(environ, start_response):
    uri = environ["REQUEST_URI"]
    if "pintest" in uri:
        try:
            uri = censor_password_from_pintest_uri(uri)
        except Exception as e:
            log.warning(e)

    uwsgi.set_logvar("clean_uri", uri)

    return django_app(environ, start_response)


if UWSGI_PRESENT:
    # If we are running the app under uWSGI we can and want to censor the access logs
    application = uwsgi_app
else:
    # If we are running it locally or in tests we can't import uwsgi so we can't censor the logs
    application = django_app
