import os
import unittest

from internalprocesses import FishbowlClient


class FishbowlClientTest(unittest.TestCase):
    VALID_CREDENTIALS = {
        "username": "danny",
        "password": os.getenv("FISHBOWL-PW"),
        "host": "factorywheelwarehouse.myfishbowl.com",
        "port": 28192
    }

    INVALID_CREDENTIALS = {
        "username": "USER",
        "password": "PASSWORD",
        "host": "factorywheelwarehouse.myfishbowl.com",
        "port": 28192
    }

    def test_login_logout_with_valid_credentials(self):
        fishbowl = FishbowlClient(**self.VALID_CREDENTIALS)
        self.assertEqual(1000, fishbowl.statusCode)
        fishbowl.close()
        self.assertEqual(1164, fishbowl.statusCode)

    def test_login_with_invalid_credentials(self):
        self.assertRaises(Exception, FishbowlClient,
                          **self.INVALID_CREDENTIALS)
