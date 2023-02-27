import json
import unittest

from internalprocesses.tracking.util import *
from internalprocesses.tracking.constants import *


class TestUtil(unittest.TestCase):

    def test_tracking_is_valid_fedex(self):
        tracking_numbers = ["0", "394648002863", "1ZRW16610308553851"]
        self.assertFalse(tracking_is_valid(tracking_numbers[0], FEDEX))
        self.assertFalse(tracking_is_valid(tracking_numbers[0], UPS))
        self.assertTrue(tracking_is_valid(tracking_numbers[1], FEDEX))
        self.assertTrue(tracking_is_valid(tracking_numbers[2], UPS))

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

    def test_get_tracking_candidates_with_candidates(self):
        with open(r"tests\mock\tracking\mock_email_1.json") as file:
            mock_email_1 = json.load(file)
        with open(r"tests\mock\tracking\mock_email_2.json") as file:
            mock_email_2 = json.load(file)

        # Use None for outlook since email contains candidates
        self.assertEqual(
            {"394648002863"},
            get_tracking_candidates(
                [mock_email_1], None, TRACKING_PATTERNS[FEDEX]
            )
        )
        self.assertEqual(
            {"1ZRW16610308553851", "1ZRW16610308553860"},
            get_tracking_candidates(
                [mock_email_2], None, TRACKING_PATTERNS[UPS]
            )
        )
        self.assertEqual(
            {"166103085538"},
            get_tracking_candidates(
                [mock_email_2], None, TRACKING_PATTERNS[FEDEX]
            )
        )

    def test_get_tracking_candidates_no_candidates(self):
        with open(r"tests\mock\tracking\mock_email_1.json") as file:
            mock_email_1 = json.load(file)

        # Expect AttributeError when trying to get attachments from None
        self.assertRaises(
            AttributeError,
            get_tracking_candidates,
            [mock_email_1],
            None,
            TRACKING_PATTERNS[UPS]
        )
