import pytest

from src.domain.vendor.sku_map_config import SkuMapConfig
from src.util.constants.inventory import HIGH_COST_MARGIN
from src.util.constants.inventory import HIGH_COST_THRESHOLD
from src.util.constants.inventory import LOW_COST_MARGIN
from src.util.inventory import pricing_util


def test_get_margin_uses_threshold():
    assert pricing_util.get_margin(HIGH_COST_THRESHOLD - 1) == LOW_COST_MARGIN
    assert pricing_util.get_margin(HIGH_COST_THRESHOLD) == HIGH_COST_MARGIN


def test_get_marked_up_price_rounds_to_cents():
    price = pricing_util.get_marked_up_price(100.0, shipping=5.5)
    expected = round(100.0 * LOW_COST_MARGIN + 5.5, 2)
    assert price == expected


def test_get_list_price_wraps_marked_up_price(mocker):
    mocker.patch(
        "src.util.inventory.pricing_util.get_marked_up_price",
        return_value=123.45,
    )

    sku, price = pricing_util.get_list_price("ALY12345A12", 10.0, 2.0)

    assert sku == "ALY12345A12"
    assert price == 123.45


def test_get_sku_map_reads_columns(mocker):
    ftp = mocker.Mock()
    ftp.get_file_as_list.return_value = [
        ["vendor-1", "inhouse-1"],
        ["vendor-2", "inhouse-2"],
    ]
    config = SkuMapConfig(
        file_path="/tmp/map.csv",
        vendor_part_number_column=0,
        inhouse_part_number_column=1,
    )
    coast_vendor_config = type("Config", (), {"sku_map_config": config})

    result = pricing_util.get_sku_map(ftp, coast_vendor_config)

    ftp.get_file_as_list.assert_called_once_with("/tmp/map.csv")
    assert result == {"vendor-1": "inhouse-1", "vendor-2": "inhouse-2"}


def test_get_stats_formats_summary():
    stats = pricing_util.get_stats(
        [["sku-1", 100.0], ["sku-2", 200.0], ["sku-3", 300.0]]
    )
    assert "Low: 100.0" in stats
    assert "High: 300.0" in stats
    assert "Average: 200.0" in stats
    assert "Median: 200.0" in stats
