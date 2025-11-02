import unittest
from unittest.mock import MagicMock, patch

from src.util.tracking import TrackingChecker
from src.util.tracking.constants import FEDEX


class TestTrackingChecker(unittest.TestCase):

    def _mock_response(self, mock_request, code=200):
        response = MagicMock()
        response.status_code = code
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
        checker._request = MagicMock(return_value={"meta": {"code": 200}})

        tracker_data = [(str(i), FEDEX, f"order-{i}") for i in range(45)]
        checker.batch_add_tracking(tracker_data)

        checker._request.assert_called()

    def test_delete_tracking_calls_request(self):
        checker = TrackingChecker()
        checker._request = MagicMock(return_value={"meta": {"code": 200}})

        checker.delete_tracking("123", FEDEX)
        checker._request.assert_called_once()

    @patch("src.util.tracking.tracking_checker.requests.request")
    def test_get_tracking_handles_invalid_json(self, mock_request):
        response = MagicMock()
        response.status_code = 200
        response.text = "invalid"
        response.json.side_effect = ValueError("bad json")
        mock_request.return_value = response

        checker = TrackingChecker()
        result = checker.get_tracking_details("123", FEDEX)

        self.assertIsNone(result)
        self.assertNotEqual(200, checker.status_code)
