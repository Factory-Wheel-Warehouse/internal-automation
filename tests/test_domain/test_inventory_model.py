from types import SimpleNamespace

import pytest

from src.domain.inventory.inventory import Inventory
from src.util.constants.inventory import (
    CORE_INVENTORY_KEY,
    FINISH_INVENTORY_KEY,
    INHOUSE_VENDOR_KEY,
    NO_VENDOR,
)


def _empty_inventory():
    inventory = Inventory.__new__(Inventory)
    inventory._vendor_configs = []
    inventory.inventory = {CORE_INVENTORY_KEY: {}, FINISH_INVENTORY_KEY: {}}
    return inventory


def test_core_in_stock_inhouse_decrements_quantity(monkeypatch):
    inventory = _empty_inventory()
    inventory.inventory[CORE_INVENTORY_KEY]["CORE123"] = {
        INHOUSE_VENDOR_KEY: [2, 0.0]
    }
    monkeypatch.setattr(
        "src.domain.inventory.inventory.get_core_search_value",
        lambda part: "CORE123",
    )

    assert inventory._core_in_stock_inhouse("ALY12345", 1)
    assert (
        inventory.inventory[CORE_INVENTORY_KEY]["CORE123"][INHOUSE_VENDOR_KEY][0]
        == 1
    )


def test_handle_zero_cost_returns_existing_cost():
    inventory = _empty_inventory()
    inventory.inventory[FINISH_INVENTORY_KEY]["SKU1"] = {
        "VendorA": [1, 25.0]
    }

    assert inventory.handle_zero_cost("SKU1", "VendorA") == 25.0
    assert inventory.handle_zero_cost("SKU1", "Missing") == 0.0


def test_get_cheapest_vendor_prefers_finish_inventory(monkeypatch):
    inventory = _empty_inventory()
    inventory.inventory[FINISH_INVENTORY_KEY]["SKU1"] = {
        "VendorA": [2, 50.0],
        "VendorB": [2, 30.0],
    }

    vendor, cost, source = inventory.get_cheapest_vendor("SKU1", 1)

    assert vendor == "VendorB"
    assert cost == 30.0
    assert source == FINISH_INVENTORY_KEY


def test_get_cheapest_vendor_returns_no_vendor_when_empty(monkeypatch):
    inventory = _empty_inventory()
    vendor, cost, source = inventory.get_cheapest_vendor("SKU1", 1)
    assert vendor == NO_VENDOR
    assert cost == 0.0
    assert source == ""


def test_convert_to_entries_uses_vendor_handling_times():
    def handling_time(sku, status):
        return 4 if status == "FINISH" else 10

    vendor_config = SimpleNamespace(
        vendor_name="VendorA",
        get_handling_time=lambda sku, status: handling_time(sku, status),
    )

    inventory = _empty_inventory()
    inventory._vendor_configs = [vendor_config]
    inventory.inventory[FINISH_INVENTORY_KEY]["SKU1"] = {
        "VendorA": [2, 75.0]
    }

    entries = inventory.convert_to_entries()

    assert len(entries) == 1
    entry = entries[0]
    assert entry.sku == "SKU1"
    assert entry.finish_status == FINISH_INVENTORY_KEY
    assert entry.availability[0].vendor_name == "VendorA"
    assert entry.availability[0].handling_time == 4
