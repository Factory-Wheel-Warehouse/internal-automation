import unittest

from internalprocesses.vendortracking.util import *
from internalprocesses.vendortracking.constants import *


class TrackingTest(unittest.TestCase):

    def test_fedex_tracking_is_valid(self):
        tracking_numbers = ["0" * 12, "394648002863"]
        self.assertFalse(tracking_is_valid(tracking_numbers[0], FEDEX))
        self.assertTrue(tracking_is_valid(tracking_numbers[1], FEDEX))

    def test_search_email_pdfs_fedex(self):
        with open(r"tests\mock\tracking\email_pdf_1.pdf", "rb") as f:
            mock_pdf_1 = f.read()
        with open(r"tests\mock\tracking\email_pdf_2.pdf", "rb") as f:
            mock_pdf_2 = f.read()

        self.assertEqual(
            ["394648002863"], search_email_pdfs(
                [mock_pdf_1], TRACKING_PATTERNS[FEDEX]
            )
        )
        self.assertEqual(
            ["392953640339"], search_email_pdfs(
                [mock_pdf_2], TRACKING_PATTERNS[FEDEX]
            )
        )
        self.assertEqual(
            ["394648002863", "392953640339"], search_email_pdfs(
                [mock_pdf_1, mock_pdf_2], TRACKING_PATTERNS[FEDEX]
            )
        )
