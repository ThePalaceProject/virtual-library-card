import unittest

from virtual_library_card.wsgi import (
    CensorUriException,
    censor_password_from_pintest_uri,
)


class TestCensorPassword(unittest.TestCase):
    def test_censor_password_from_pintest_uri(self):
        # If the pintest uri is in the expected form we see that the uri is censored correctly
        uri = "/api/1234567890/secret/pintest"
        expected_censored_uri = "/api/1234567890/***/pintest"
        self.assertEqual(censor_password_from_pintest_uri(uri), expected_censored_uri)

        uri = "/PATRONAPI/1234567890/secret/pintest"
        expected_censored_uri = "/PATRONAPI/1234567890/***/pintest"
        self.assertEqual(censor_password_from_pintest_uri(uri), expected_censored_uri)

        # If there is no pintest keyword nothing is censored
        uri = ""
        self.assertEqual(censor_password_from_pintest_uri(uri), uri)

        uri = "/admin/"
        self.assertEqual(censor_password_from_pintest_uri(uri), uri)

        uri = "/api/1234567890/secret"
        self.assertEqual(censor_password_from_pintest_uri(uri), uri)

        # If there is pintest keyword present but the uri is not in the expected form we get an exception
        uri = "/pintest"
        self.assertRaises(CensorUriException, censor_password_from_pintest_uri, uri)

        uri = "/secret/pintest"
        self.assertRaises(CensorUriException, censor_password_from_pintest_uri, uri)

        uri = "/api/secret/pintest"
        self.assertRaises(CensorUriException, censor_password_from_pintest_uri, uri)

        uri = "/card_number/api/secret/pintest"
        self.assertRaises(CensorUriException, censor_password_from_pintest_uri, uri)

        uri = "/api/pintest/card_number/secret"
        self.assertRaises(CensorUriException, censor_password_from_pintest_uri, uri)

        uri = "/api/1234567890/secret/extra_param/pintest"
        self.assertRaises(CensorUriException, censor_password_from_pintest_uri, uri)
