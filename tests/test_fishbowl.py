import os
import unittest

from internalprocesses import FBConnection


class FishbowlTest(unittest.TestCase):
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
        fishbowl = FBConnection(**self.VALID_CREDENTIALS)
        self.assertEqual(1000, fishbowl.statusCode)
        fishbowl.close()
        self.assertEqual(1164, fishbowl.statusCode)

    def test_login_with_invalid_credentials(self):
        self.assertRaises(Exception, FBConnection, **self.INVALID_CREDENTIALS)


if __name__ == "__main__":
    unittest.main()
