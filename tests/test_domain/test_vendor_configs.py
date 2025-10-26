import pytest

from src.domain.inventory.finish_status_type import FinishStatusType
from src.domain.order.address import Address
from src.domain.vendor.cost_map_config import CostMapConfig
from src.domain.vendor.handling_time_config import HandlingTimeConfig
from src.domain.vendor.handling_time_map import HandlingTimeMap
from src.domain.vendor.inventory_file_config import InventoryFileConfig
from src.domain.vendor.vendor_config import VendorConfig


def _handling_time_config(core_default: int = 1, finished_default: int = 2):
    return HandlingTimeConfig(
        core_handling_times=HandlingTimeMap(default=core_default),
        finished_handling_times=HandlingTimeMap(default=finished_default),
    )


def _inventory_file_config(cost_column: int | None):
    return InventoryFileConfig(
        part_number_column=0,
        quantity_column=1,
        file_path="/tmp/vendor.csv",
        cost_column=cost_column,
    )


def _address():
    return Address(
        name="Test Vendor",
        street1="123 Main St",
        city="Austin",
        state="TX",
        zipcode="73301",
    )


def test_inventory_file_config_requires_single_path():
    with pytest.raises(Exception):
        InventoryFileConfig(part_number_column=0, quantity_column=1)

    with pytest.raises(Exception):
        InventoryFileConfig(
            part_number_column=0,
            quantity_column=1,
            file_path="/tmp/file.csv",
            dir_path="/tmp/dir",
        )


def test_inventory_file_config_accepts_either_path():
    config = InventoryFileConfig(
        part_number_column=0,
        quantity_column=1,
        dir_path="/tmp",
    )
    assert config.dir_path == "/tmp"


def test_cost_map_config_enforces_single_path():
    with pytest.raises(Exception):
        CostMapConfig()

    with pytest.raises(Exception):
        CostMapConfig(file_path="a.csv", dir_path="/tmp")


def test_vendor_config_requires_cost_source_exclusivity():
    handling_time_config = _handling_time_config()

    with pytest.raises(Exception):
        VendorConfig(
            vendor_name="NoCostData",
            address=_address(),
            inventory_file_config=_inventory_file_config(cost_column=None),
            handling_time_config=handling_time_config,
        )

    with pytest.raises(Exception):
        VendorConfig(
            vendor_name="BothCostSources",
            address=_address(),
            inventory_file_config=_inventory_file_config(cost_column=2),
            handling_time_config=handling_time_config,
            cost_map_config=CostMapConfig(file_path="map.csv"),
        )


def test_vendor_config_accepts_exactly_one_cost_source():
    vendor = VendorConfig(
        vendor_name="JustCostColumn",
        address=_address(),
        inventory_file_config=_inventory_file_config(cost_column=2),
        handling_time_config=_handling_time_config(),
    )
    assert vendor.inventory_file_config.cost_column == 2

    vendor_with_map = VendorConfig(
        vendor_name="JustCostMap",
        address=_address(),
        inventory_file_config=_inventory_file_config(cost_column=None),
        handling_time_config=_handling_time_config(),
        cost_map_config=CostMapConfig(file_path="map.csv"),
    )
    assert vendor_with_map.cost_map_config.file_path == "map.csv"


def test_handling_time_config_returns_status_specific_values():
    handling_map = _handling_time_config(core_default=1, finished_default=3)
    handling_map.core_handling_times.ucode_map["123"] = 5
    handling_map.finished_handling_times.ucode_map["123"] = 7

    assert handling_map.get("123", FinishStatusType.CORE) == 5
    assert handling_map.get("999", FinishStatusType.CORE) == 1
    assert handling_map.get("123", FinishStatusType.FINISHED) == 7
    assert handling_map.get("999", FinishStatusType.FINISHED) == 3
