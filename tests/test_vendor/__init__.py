import json
import unittest

from internalprocesses.vendor import VendorConfig


class TestVendor(unittest.TestCase):
    def test_vendor_initialization_with_valid_data(self):
        with open("../mock/vendor/test_vendor_configs.json") as file:
            vendor_data = json.load(file)
        vendors = [VendorConfig(**v) for v in vendor_data]
        self.assertEqual(len(vendors), 7)
