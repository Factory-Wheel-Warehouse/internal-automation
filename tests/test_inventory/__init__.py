import unittest

from internalprocesses.inventory import Inventory
from src.domain.inventory.constants import CORE_INVENTORY_KEY, \
    FINISH_INVENTORY_KEY, INHOUSE_VENDOR_KEY


class TestInventory(unittest.TestCase):
    inventory = Inventory(None, None, None)

    def _reset_inventory(self):
        self.inventory.inventory = {
            CORE_INVENTORY_KEY: {
                "ALY12345U": {
                    INHOUSE_VENDOR_KEY: [5, 0],
                    "Vendor1": [5, 65]
                },
                "ALY23456U": {
                    "Vendor1": [5, 0]
                }
            },
            FINISH_INVENTORY_KEY: {
                "ALY12345U10": {
                    INHOUSE_VENDOR_KEY: [2, 0],
                    "Vendor1": [3, 115]
                },
                "ALY12345U20": {
                    "Vendor2": [2, 100]
                },
                "ALY12345U30": {
                    "Vendor3": [3, 45]
                },
                "ALY12345U95": {
                    "Vendor4": [2, 275]
                },
                "ALY23456U15": {
                    "Vendor1": [1, 75]
                }
            }
        }

    def test_inhouse_core_assignment(self):
        self._reset_inventory()
        vendor = self.inventory.get_cheapest_vendor("ALY12345U20", 5)
        self.assertEqual(vendor, (INHOUSE_VENDOR_KEY, 0))

    def test_vendor1_core_assignment(self):
        self._reset_inventory()
        self.inventory.get_cheapest_vendor("ALY12345U20", 5)
        vendor = self.inventory.get_cheapest_vendor("ALY12345U20", 5)
        self.assertEqual(vendor, ("Vendor1", 65))

    def test_vendor4_polished_assignment(self):
        self._reset_inventory()
        vendor = self.inventory.get_cheapest_vendor("ALY12345U95", 2)
        self.assertEqual(vendor, ("Vendor4", 275))

    def test_assign_inhouse_cores_then_finish(self):
        self._reset_inventory()
        vendor = self.inventory.get_cheapest_vendor("ALY12345U20", 5)
        self.assertEqual(vendor, (INHOUSE_VENDOR_KEY, 0))
        vendor = self.inventory.get_cheapest_vendor("ALY12345U20", 2)
        self.assertEqual(vendor, ("Vendor2", 100))

    def test_zero_cost_price_match(self):
        self._reset_inventory()
        vendor = self.inventory.get_cheapest_vendor("ALY23456U15", 4)
        self.assertEqual(vendor, ("Vendor1", 75))
