from types import SimpleNamespace

import pandas as pd
import pytest

from src.util.constants.inventory import (
    CORE_INVENTORY_KEY,
    FINISH_INVENTORY_KEY,
    LISTABLE_SKUS_PATH,
    MISSING_SKUS_PATH,
)
from src.util.inventory import master_inventory_util as miu


def test_get_initial_dataframe_includes_vendor_headers():
    vendors = [SimpleNamespace(vendor_name="Vendor A"), SimpleNamespace(vendor_name="Vendor B")]
    df = miu.get_initial_dataframe(vendors)
    assert "vendor_a_cost" in df.columns
    assert "vendor_b_cost" in df.columns


def test_get_skus_missing_data_returns_empty_on_error(mocker):
    ftp = mocker.Mock()
    ftp.get_file_as_list.side_effect = miu.EmptyDataError("empty")
    assert miu._get_skus_missing_data(ftp) == []


def test_build_total_inventory_merges_core_and_finish(mocker):
    inventory = SimpleNamespace(
        inventory={
            FINISH_INVENTORY_KEY: {"ALY12345A12": {"VendorA": [1, 10.0]}},
            CORE_INVENTORY_KEY: {"ALY12345": {"VendorB": [2, 5.0]}},
        }
    )
    data_store = {
        LISTABLE_SKUS_PATH: [["ALY12345A12"], ["INVALID"]],
        MISSING_SKUS_PATH: [["ALY00000A12"]],
    }

    def get_file_as_list(path):
        return data_store[path]

    ftp = SimpleNamespace(
        get_file_as_list=get_file_as_list,
        write_list_as_csv=mocker.Mock(),
    )

    total = miu.build_total_inventory(inventory, ftp)

    assert "ALY12345A12" in total
    ftp.write_list_as_csv.assert_called_once()


def test_add_core_equivalents_to_total_appends_quantities():
    total = {"ALY12345A12": {"VendorB": [0, 5.0, 1]}}
    finishes = {"ALY12345A12"}
    core_availability = {"VendorB": [2, 5.0]}

    miu.add_core_equivalents_to_total(total, finishes, core_availability)
    assert total["ALY12345A12"]["VendorB"][2] == 3


def test_populate_dataframe_returns_rows(mocker):
    ftp = mocker.Mock()
    ftp.get_file_as_list.return_value = [["ALY12345A12", 150.0]]
    vendors = [SimpleNamespace(vendor_name="VendorA", inventory_file_config=SimpleNamespace(quantity_deduction=None), handling_time_config=None)]
    total_inventory = {"ALY12345A12": {"VendorA": [2, 50.0]}}
    df = miu.get_initial_dataframe(vendors)

    populated = miu.populate_dataframe(total_inventory, df, ftp, vendors)
    assert not populated.empty


class DummyVendor(SimpleNamespace):
    def get_handling_time(self, ucode, status):
        return 7 if status == "FINISHED" else 9


def test_get_sku_handling_time_prefers_vendor_config():
    vendor = DummyVendor(handling_time_config=True)
    assert miu._get_sku_handling_time("ALY12345A12", True, vendor) == 7
    assert miu._get_sku_handling_time("ALY12345A12", False, None) == 3


def test_get_acceptable_ht_returns_upper_bound():
    assert miu._get_acceptable_ht(4, [1, 3, 5]) == 5
    assert miu._get_acceptable_ht(10, [1, 3, 5]) == 6


def test_get_formatted_row_populates_vendor_fields():
    vendors = {
        "VendorA": DummyVendor(
            vendor_name="VendorA",
            inventory_file_config=SimpleNamespace(quantity_deduction=None),
            handling_time_config=True,
        )
    }
    availability = {"VendorA": [2, 50.0]}
    row = miu._get_formatted_row("ALY12345A12", availability, price=120.0, vendors=vendors)
    assert row["vendora_cost"] == 50.0
    assert row["total_qty"] == 2


def test_get_combined_qty_respects_deduction():
    vendor = SimpleNamespace(inventory_file_config=SimpleNamespace(quantity_deduction=3))
    assert miu._get_combined_qty(5, 0, vendor) == 2
    assert miu._get_combined_qty(1, 0, vendor) == 0


def test_margin_and_price_helpers():
    assert miu._get_margin(100.0) == miu.LOW_COST_MARGIN
    assert miu._get_margin(500.0) == miu.HIGH_COST_MARGIN
    price = miu._get_price(100.0, 10.0)
    assert price > 0
