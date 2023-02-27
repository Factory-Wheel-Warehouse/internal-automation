import unittest

from internalprocesses.tracking import TrackingChecker
from internalprocesses.tracking.constants import FEDEX


class TestTrackingChecker(unittest.TestCase):

    def test_add_tracking(self):
        tracking_checker = TrackingChecker()
        tracking_checker.add_single_tracking("394648002863", FEDEX, "test")
        self.assertTrue(tracking_checker.status_code in [200, 4016])

    def test_check_tracking(self):
        tracking_checker = TrackingChecker()
        tracking_checker.check_tracking("394648002863", FEDEX)
        self.assertEqual(200, tracking_checker.status_code)

    # Failing due to 500 server error? Look into
    # def test_delete_tracking(self):
    #     tracking_checker = TrackingChecker()
    #     tracking_checker.delete_tracking("394648002863", FEDEX)
    #     self.assertEqual(200, tracking_checker.status_code)
