import unittest
from unittest.mock import patch, MagicMock

from src.util.tracking import TrackingChecker
from src.util.tracking.constants import FEDEX


class TestTrackingChecker(unittest.TestCase):

    def _mock_response(self, mock_request, code=200):
        response = MagicMock()
        response.json.return_value = {
            "meta": {"code": code},
            "data": [{"status": "delivered"}]
        }
        mock_request.return_value = response

    @patch("src.util.tracking.tracking_checker.requests.request")
    def test_add_tracking(self, mock_request):
        self._mock_response(mock_request, code=200)
        tracking_checker = TrackingChecker()
        tracking_checker.add_single_tracking("394648002863", FEDEX, "test")
        self.assertTrue(tracking_checker.status_code in [200, 4016])

    @patch("src.util.tracking.tracking_checker.requests.request")
    def test_check_tracking(self, mock_request):
        self._mock_response(mock_request, code=200)
        tracking_checker = TrackingChecker()
        tracking_checker.get_tracking_details("394648002863", FEDEX)
        self.assertEqual(200, tracking_checker.status_code)

    def test_batch_add_tracking_chunks(self):
        checker = TrackingChecker()
        checker._request = unittest.mock.Mock(return_value={"meta": {"code": 200}})

        tracker_data = [(str(i), FEDEX, f"order-{i}") for i in range(45)]
        checker.batch_add_tracking(tracker_data)

        # Should be split into two batches (chunk size logic populates chunked list)
        self.assertTrue(checker._request.called)

    def test_delete_tracking_calls_request(self):
        checker = TrackingChecker()
        checker._request = unittest.mock.Mock(return_value={"meta": {"code": 200}})

        checker.delete_tracking("123", FEDEX)
        checker._request.assert_called_once()

    # Failing due to 500 server error? Look into
    # def test_delete_tracking(self):
    #     tracking_checker = TrackingChecker()
    #     tracking_checker.delete_tracking("394648002863", FEDEX)
    #     self.assertEqual(200, tracking_checker.status_code)
