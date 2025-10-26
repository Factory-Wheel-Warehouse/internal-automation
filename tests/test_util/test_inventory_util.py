import math
from types import SimpleNamespace

import pytest

from src.domain.vendor.cost_config import CostConfig
from src.domain.vendor.inclusion_config import InclusionConfig
from src.domain.vendor.paint_code_cost_adjustment import \
    PaintCodeCostAdjustment
from src.util.constants.inventory import CORE_INVENTORY_KEY
from src.util.constants.inventory import FINISH_INVENTORY_KEY
from src.util.constants.inventory import MINIMUM_MARGIN
from src.domain.vendor.classification_config import ClassificationConfig
from src.domain.vendor.inventory_file_config import InventoryFileConfig
from src.domain.vendor.sku_map_config import SkuMapConfig
from src.util.inventory import inventory_util as inv_util


def test_get_adjusted_cost_applies_material_and_ucode_adjustments():
    config = CostConfig(
        alloy_adjustment=3.0,
        steel_adjustment=2.0,
        general_adjustment=5.0,
        ucode_adjustment=PaintCodeCostAdjustment(
            default=0.0,
            ucodes={"12": 1.5}
        )
    )

    adjusted = inv_util.get_adjusted_cost("ALY12345A12", 100.0, config)

    # Start with base 100, +3 alloy adjustment, +1.5 ucode, +5 general
    assert adjusted == pytest.approx(109.5)


def test_add_to_inventory_merges_quantities_and_truncates_core_part_numbers():
    inventory = {
        CORE_INVENTORY_KEY: {},
        FINISH_INVENTORY_KEY: {}
    }

    inv_util._add_to_inventory(
        inventory,
        CORE_INVENTORY_KEY,
        "ALY12345A12N",
        "Vendor A",
        qty=2,
        cost=50.0
    )
    inv_util._add_to_inventory(
        inventory,
        CORE_INVENTORY_KEY,
        "ALY12345A12N",
        "Vendor A",
        qty=3,
        cost=50.0
    )
    inv_util._add_to_inventory(
        inventory,
        CORE_INVENTORY_KEY,
        "ALY12345A12N",
        "Vendor B",
        qty=1,
        cost=55.0
    )

    stored_part_numbers = list(inventory[CORE_INVENTORY_KEY].keys())
    assert stored_part_numbers == ["ALY12345A"]
    vendor_a_qty = inventory[CORE_INVENTORY_KEY]["ALY12345A"]["Vendor A"][0]
    assert vendor_a_qty == 5
    assert inventory[CORE_INVENTORY_KEY]["ALY12345A"]["Vendor B"] == [1, 55.0]


def test_include_row_item_smoke_checks():
    # NaN cost immediately excludes
    assert not inv_util.include_row_item([], None, math.nan, 0.0, "ALY12345A12N")

    # Margin violation excludes
    assert not inv_util.include_row_item([], None, 10.0, 10.0, "ALY12345A12N")

    # Paint code 95 excluded
    assert not inv_util.include_row_item([], None, 10.0,
                                         10.0 * (MINIMUM_MARGIN + 1),
                                         "ALY12345A95N")


def test_include_row_item_honors_inclusion_config():
    row = ["", "", "include_me"]
    config = InclusionConfig(
        inclusion_condition_column=2,
        inclusion_condition="condition == 'include_me'",
        exclusion_condition="condition == 'exclude_me'",
    )

    include = inv_util.include_row_item(
        row, config, cost=20.0, price=40.0, part_num="ALY12345A12N"
    )
    assert include

    row[2] = "exclude_me"
    include = inv_util.include_row_item(
        row, config, cost=20.0, price=40.0, part_num="ALY12345A12N"
    )
    assert not include


def test_get_core_search_value_filters_replica_and_polished_codes():
    base = "ALY12345A12"
    assert inv_util.get_core_search_value(base) == base[:9]

    replica = "ALY12345A12N"
    assert inv_util.get_core_search_value(replica) is None

    polished = "ALY12345A99"
    assert inv_util.get_core_search_value(polished) is None


def test_get_price_map_reads_master_pricing(mocker):
    ftp = SimpleNamespace()
    ftp.get_file_as_list = mocker.Mock(return_value=[["ALY12345A12N", "199.0"]])

    price_map = inv_util.get_price_map(ftp)

    ftp.get_file_as_list.assert_called_once()
    assert price_map == {"ALY12345A12N": 199.0}


def test_eval_conditions_returns_matching_branch():
    row = ["", "finish"]
    assert inv_util._eval_conditions("condition == 'finish'", None, 1, row) == 1
    assert inv_util._eval_conditions(None, "condition == 'finish'", 1, row) == 2


def test_build_map_from_config_handles_collisions():
    config = SkuMapConfig(file_path="/tmp/map.csv", vendor_part_number_column=0, inhouse_part_number_column=1)
    ftp = SimpleNamespace()
    ftp.get_file_as_list = lambda path, encoding="utf-8": [
        ["abc", "one"],
        ["abc", "two"],
        ["xyz", "foo"],
    ]
    mapping = inv_util.build_map_from_config(ftp, config)
    assert mapping == {"ABC": "ONE", "XYZ": "FOO"}


def test_get_part_number_prefers_sku_map():
    row = ["abc"]
    sku_map = {"ABC": "SKU123"}
    assert inv_util._get_part_number(row, 0, sku_map) == "SKU123"


def test_get_price_uses_cache_and_generates_when_missing(mocker):
    mocker.patch("src.util.inventory.inventory_util.get_marked_up_price", return_value=120.0)
    price_map = {"SKU123": 99.0}
    assert inv_util._get_price(price_map, "SKU123", 0) == 99.0
    price = inv_util._get_price(price_map, "ALY12345A12N", 10.0)
    assert price == 120.0
    assert price_map["ALY12345A12N"] == 120.0


def test_get_inventory_key_and_min_qty_respects_classification():
    config = ClassificationConfig(classification_condition_column=0, core_condition="condition == 'core'", finish_condition="condition == 'finish'")
    assert inv_util._get_inventory_key_and_min_qty("ALY12345A", ["core"], config)[0] == inv_util.CORE_INVENTORY_KEY
    assert inv_util._get_inventory_key_and_min_qty("ALY12345A12", ["finish"], config)[0] == inv_util.FINISH_INVENTORY_KEY


def test_get_inhouse_paint_code_extracts_numeric_code():
    assert inv_util._get_inhouse_paint_code("ALY12345A12") == 12
    assert inv_util._get_inhouse_paint_code("ALY1") == -1


def test_get_file_uses_dir_when_present(mocker):
    config = InventoryFileConfig(part_number_column=0, quantity_column=1, dir_path="/tmp")
    ftp = SimpleNamespace(get_directory_most_recent_file=mocker.Mock(return_value=[["a"]]))
    rows = inv_util._get_file(ftp, config)
    assert rows == [["a"]]


def test_get_part_cost_prefers_cost_map():
    vendor = SimpleNamespace(inventory_file_config=SimpleNamespace(cost_column=0))
    assert inv_util._get_part_cost({"PN": "10"}, "PN", [], vendor) == 10.0
    assert inv_util._get_part_cost({}, "PN", ["not-a-number"], vendor) == -1


def test_get_qty_handles_invalid_values():
    vendor = SimpleNamespace(inventory_file_config=SimpleNamespace(quantity_column=0))
    assert inv_util._get_qty(["5"], vendor) == 5
    assert inv_util._get_qty(["NaN"], vendor) == -1


def test_add_vendor_inventory_runs_happy_path(mocker):
    ftp = mocker.Mock()
    inventory = {inv_util.CORE_INVENTORY_KEY: {}, inv_util.FINISH_INVENTORY_KEY: {}}
    vendor = SimpleNamespace(
        vendor_name="Vendor",
        inventory_file_config=SimpleNamespace(part_number_column=0, quantity_column=1, cost_column=2),
        classification_config=None,
        inclusion_config=None,
        cost_adjustment_config=None,
    )
    mocker.patch("src.util.inventory.inventory_util._get_file", return_value=[["row"]])
    mocker.patch("src.util.inventory.inventory_util._get_part_number", return_value="ALY12345A12")
    mocker.patch("src.util.inventory.inventory_util._get_inventory_key_and_min_qty", return_value=(inv_util.FINISH_INVENTORY_KEY, 1))
    mocker.patch("src.util.inventory.inventory_util._get_part_cost", return_value=10.0)
    mocker.patch("src.util.inventory.inventory_util.get_adjusted_cost", return_value=10.0)
    mocker.patch("src.util.inventory.inventory_util._get_price", return_value=20.0)
    mocker.patch("src.util.inventory.inventory_util.include_row_item", return_value=True)
    mocker.patch("src.util.inventory.inventory_util._get_qty", return_value=5)
    add_mock = mocker.patch("src.util.inventory.inventory_util._add_to_inventory")

    inv_util.add_vendor_inventory(ftp, inventory, vendor, {}, {}, {})

    add_mock.assert_called_once()


def test_add_inhouse_inventory_populates_buckets():
    inventory = {inv_util.CORE_INVENTORY_KEY: {}, inv_util.FINISH_INVENTORY_KEY: {}}
    report = ["header", '"ALY12345A12N","2","0"']
    inv_util.add_inhouse_inventory(inventory, report)
    assert "ALY12345A12N" in inventory[inv_util.FINISH_INVENTORY_KEY]
