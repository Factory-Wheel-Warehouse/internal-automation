from src.domain.vendor import VendorConfig
from src.facade.ftp.ftp_facade import FTPFacade
from src.util.constants.inventory import DOLLAR_ROUND_DIGITS
from src.util.constants.inventory import HIGH_COST_MARGIN
from src.util.constants.inventory import HIGH_COST_THRESHOLD
from src.util.constants.inventory import LOW_COST_MARGIN


def get_margin(cost: float):
    if cost < HIGH_COST_THRESHOLD:
        return LOW_COST_MARGIN
    else:
        return HIGH_COST_MARGIN


def get_marked_up_price(cost: float, shipping: float = 0.0) -> float:
    margin = get_margin(cost)
    return round(cost * margin + shipping, DOLLAR_ROUND_DIGITS)


def get_list_price(sku: str, base_cost: float, cost_adjustment: float):
    return [sku, get_marked_up_price(base_cost, cost_adjustment)]


def get_sku_map(ftp: FTPFacade, coast_vendor_config: VendorConfig):
    map_file = ftp.get_file_as_list(
        coast_vendor_config.sku_map_config.file_path)
    map_ = {}
    sku_map_config = coast_vendor_config.sku_map_config
    vendor_part_col = sku_map_config.vendor_part_number_column
    inhouse_part_col = sku_map_config.inhouse_part_number_column
    for row in map_file:
        map_[row[vendor_part_col]] = row[inhouse_part_col]
    return map_


def get_stats(ascending_prices: list[list[str, float]]):
    sum_ = sum([p[1] for p in ascending_prices])
    return f"Low: {ascending_prices[0][1]}\n" \
           f"High: {ascending_prices[-1][1]}\n" \
           f"Average: {sum_ / len(ascending_prices)}\n" \
           f"Median: {ascending_prices[len(ascending_prices) // 2][1]}"
