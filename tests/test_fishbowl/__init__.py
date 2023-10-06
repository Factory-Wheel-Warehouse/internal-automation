import os
import unittest

from internalprocesses import FishbowlFacade


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
        fishbowl = FishbowlFacade(**self.VALID_CREDENTIALS)
        self.assertEqual(1000, fishbowl.general_status)
        fishbowl.close()
        self.assertEqual(1164, fishbowl.general_status)

    def test_login_with_invalid_credentials(self):
        self.assertRaises(Exception, FishbowlFacade,
                          **self.INVALID_CREDENTIALS)
