from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost"]

##
# Set this setting to True when deploying the API. It will only make available the API urls.
##
HAS_API = True
HAS_WEBSITE = True

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "virtual_library_card_dev",
        "USER": "vlc",
        "PASSWORD": "test",
        "HOST": os.environ.get("VLC_DEV_DB_HOST", "pg"),
        "PORT": os.environ.get("VLC_DEV_DB_PORT", "5432"),
        "OPTIONS": {"sslmode": os.environ.get("VLC_DEV_DB_SSL_MODE", "require")},
    }
}

# Testing ONLY
SILENCED_SYSTEM_CHECKS = ["django_recaptcha.recaptcha_test_key_error"]

ABSOLUTEURI_PROTOCOL = "http"
DATE_INPUT_FORMATS = ["%m-%d-%Y"]
CSRF_COOKIE_DOMAIN = None

ROOT_URL = "http://localhost:8000"  # Needed for self referential links (like emails)

# The default value for the HTML_MINIFY setting is not DEBUG. You only need to set it to True if you want to minify your HTML code when DEBUG is enabled.
HTML_MINIFY = True

# These are all dummy values for testing
MAPQUEST_API_KEY = "xxx"

EMAIL_HOST = "xxx"
EMAIL_PORT = "xxx"
EMAIL_HOST_USER = "xxx"
EMAIL_HOST_PASSWORD = "xxx"
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = "xxx"

SECRET_KEY = "xxx"

ABSOLUTEURI_PROTOCOL = "http"

# Testing specific keys
# https://developers.google.com/recaptcha/docs/faq#id-like-to-run-automated-tests-with-recaptcha.-what-should-i-do
RECAPTCHA_PUBLIC_KEY = "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
RECAPTCHA_PRIVATE_KEY = "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"

DEFAULT_FILE_STORAGE = "virtual_library_card.storage.S3PublicStorage"
STATICFILES_STORAGE = "virtual_library_card.storage.S3StaticStorage"
AWS_STORAGE_BUCKET_NAME = "vlc-test"
if "VLC_DEV_AWS_S3_ENDPOINT_URL" in os.environ:
    AWS_S3_ENDPOINT_URL = os.environ["VLC_DEV_AWS_S3_ENDPOINT_URL"]
elif (
    "VLC_DEV_AWS_S3_ENDPOINT_URL_HOST" in os.environ
    and "VLC_DEV_AWS_S3_ENDPOINT_URL_PORT" in os.environ
):
    AWS_S3_ENDPOINT_URL = (
        f"http://{os.environ['VLC_DEV_AWS_S3_ENDPOINT_URL_HOST']}"
        f":{os.environ['VLC_DEV_AWS_S3_ENDPOINT_URL_PORT']}"
    )
else:
    AWS_S3_ENDPOINT_URL = "http://localhost:9000"

AWS_S3_CUSTOM_DOMAIN = os.environ.get("VLC_DEV_AWS_S3_CUSTOM_DOMAIN", False)
AWS_S3_URL_PROTOCOL = os.environ.get("VLC_DEV_AWS_S3_URL_PROTOCOL", "https:")

# Either profile session name or a key/secret MUST be present
# In case key/secret is the way to go, please delete the session profile setting
# as it will take priority in the django-storages order
# If neither is provided the "default" profile will be used from the AWS credentials file
# AWS_S3_SESSION_PROFILE = "default"
AWS_S3_ACCESS_KEY_ID = "vlc-minio"
AWS_S3_SECRET_ACCESS_KEY = "123456789"

# Dynamic link data
DYNAMIC_LINKS = {
    "web_api_key": "test_web_key",
    "domain_uri_prefix": "https://palacetest.page.link",
    "android_package_name": "com.thepalaceproject.circulation",
    "ios_bundle_id": "123456789",
}

DYNAMIC_LINKS_SIGNUP_URL = "https://thepalaceproject.org/app"

# To adjust depending on deployment
DEFAULT_PRIVACY_URL = "https://legal.palaceproject.io/Privacy%20Policy.html"

# To allow specifying the name of the default library the superuser is associated with:
DEFAULT_SUPERUSER_LIBRARY_NAME = "Lyrasis"
DEFAULT_SUPERUSER_LIBRARY_IDENTIFIER = "lyra"
DEFAULT_SUPERUSER_LIBRARY_PREFIX = "0123"
DEFAULT_SUPERUSER_LIBRARY_STATE = "GA"
DEFAULT_SUPERUSER_FIRST_NAME = "superuser"
DEFAULT_LIBRARY_LOGO = "logo.png"
