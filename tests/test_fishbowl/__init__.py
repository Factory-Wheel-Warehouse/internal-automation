import unittest

from src.facade.fishbowl import FishbowlFacade


class FishbowlClientTest(unittest.TestCase):

    def test_login_logout(self):
        fishbowl = FishbowlFacade()
        self.assertEqual(1000, fishbowl.general_status)
        fishbowl.close()
        self.assertEqual(1164, fishbowl.general_status)
