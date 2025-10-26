import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.util.constants.tracking import FEDEX, TRACKING_PATTERNS, UPS
from src.util.tracking import util as tracking_util
from src.util.tracking.util import (
    get_tracking_candidates,
    search_email_pdfs,
    tracking_is_valid,
)

MOCK_DIR = Path(__file__).resolve().parents[1] / "mock" / "tracking"


class TestUtil(unittest.TestCase):

    def test_tracking_is_valid(self):
        tracking_numbers = ["0", "394648002863", "1ZRW16610308553851"]
        with patch("src.util.tracking.util.requests.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(text=""),
                MagicMock(text=""),
                MagicMock(text="success"),
                MagicMock(text="success"),
            ]
            self.assertFalse(tracking_is_valid(tracking_numbers[0], FEDEX))
            self.assertFalse(tracking_is_valid(tracking_numbers[0], UPS))
            self.assertTrue(tracking_is_valid(tracking_numbers[1], FEDEX))
            self.assertTrue(tracking_is_valid(tracking_numbers[2], UPS))

    def test_search_email_pdfs_fedex(self):
        with (MOCK_DIR / "email_pdf_1.pdf").open("rb") as f:
            mock_pdf_1 = f.read()
        with (MOCK_DIR / "email_pdf_2.pdf").open("rb") as f:
            mock_pdf_2 = f.read()

        self.assertEqual(
            ["394648002863"],
            search_email_pdfs([mock_pdf_1], TRACKING_PATTERNS[FEDEX]),
        )
        self.assertEqual(
            ["392953640339"],
            search_email_pdfs([mock_pdf_2], TRACKING_PATTERNS[FEDEX]),
        )
        self.assertEqual(
            ["394648002863", "392953640339"],
            search_email_pdfs([mock_pdf_1, mock_pdf_2], TRACKING_PATTERNS[FEDEX]),
        )

    def test_get_tracking_candidates_with_candidates(self):
        with (MOCK_DIR / "mock_email_1.json").open() as file:
            mock_email_1 = json.load(file)
        with (MOCK_DIR / "mock_email_2.json").open() as file:
            mock_email_2 = json.load(file)

        self.assertEqual(
            {"394648002863"},
            get_tracking_candidates(
                [mock_email_1], outlook=None, pattern=TRACKING_PATTERNS[FEDEX]
            ),
        )
        self.assertEqual(
            {"1ZRW16610308553851", "1ZRW16610308553860"},
            get_tracking_candidates(
                [mock_email_2], outlook=None, pattern=TRACKING_PATTERNS[UPS]
            ),
        )
        self.assertEqual(
            {"166103085538"},
            get_tracking_candidates(
                [mock_email_2], outlook=None, pattern=TRACKING_PATTERNS[FEDEX]
            ),
        )

    def test_get_tracking_candidates_no_candidates(self):
        with (MOCK_DIR / "mock_email_1.json").open() as file:
            mock_email_1 = json.load(file)

        self.assertRaises(
            AttributeError,
            get_tracking_candidates,
            [mock_email_1],
            None,
            TRACKING_PATTERNS[UPS],
        )

    def test_po_num_email_search_calls_outlook(self):
        outlook = MagicMock()
        outlook.searchMessages.return_value = ["email"]
        result = tracking_util.po_num_email_search("PO123", outlook)
        self.assertEqual(result, ["email"])
        outlook.searchMessages.assert_called_once_with('?$search="\\"PO123\\""', getAll=True)

    def test_get_pdf_attachments_filters_to_pdf(self):
        outlook = MagicMock()
        outlook.get_email_attachments.return_value = [
            {"contentType": tracking_util.PDF_CONTENT_TYPE, "id": "1"},
            {"contentType": "text/plain", "id": "2"},
        ]
        outlook.getEmailAttachmentContent.return_value = b"data"

        attachments = tracking_util.get_pdf_attachments("email", outlook)

        self.assertEqual(attachments, [b"data"])

    @patch("src.util.tracking.util.get_valid_tracking_numbers", return_value=["123"])
    @patch("src.util.tracking.util.get_tracking_candidates", return_value={"123"})
    @patch("src.util.tracking.util.CarrierPatterns.map", return_value=[("FEDEX", r"\\d+")])
    @patch("src.util.tracking.util.po_num_email_search", return_value=["email"])
    def test_get_tracking_from_outlook(self, mock_search, mock_map, mock_candidates, mock_valid):
        outlook = MagicMock()
        result = tracking_util.get_tracking_from_outlook("PO123", outlook)
        self.assertEqual(result, {"FEDEX": ["123"]})
