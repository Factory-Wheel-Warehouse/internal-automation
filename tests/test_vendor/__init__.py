import json
import unittest

from dacite import from_dict

from internalprocesses.vendor import VendorConfig


class TestVendor(unittest.TestCase):
    def test_vendor_initialization_with_valid_data(self):
        with open("tests/mock/vendor/test_vendor_configs.json") as file:
            vendor_data = json.load(file)
        vendors = {}
        for v in vendor_data:
            vendors[v["vendor_name"]] = from_dict(VendorConfig, v)
        self.assertEqual(len(vendors), 7)
        self.assertIsNotNone(
            vendors["Perfection"].cost_adjustment_config.ucode_adjustment)
