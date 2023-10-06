from src.domain.vendor import VendorConfig
from src.facade.ftp.ftp_facade import FTPFacade
from src.util.constants.inventory import DOLLAR_ROUND_DIGITS
from src.util.constants.inventory import HIGH_COST_MARGIN
from src.util.constants.inventory import HIGH_COST_THRESHOLD
from src.util.constants.inventory import LOW_COST_MARGIN
from src.util.inventory import get_adjusted_cost


def get_margin(cost: float):
    if cost < HIGH_COST_THRESHOLD:
        return LOW_COST_MARGIN
    else:
        return HIGH_COST_MARGIN


def get_list_price(coast_vendor_config: VendorConfig,
                   sku: str, base_cost: float):
    cost_config = coast_vendor_config.cost_adjustment_config
    adjusted_cost = get_adjusted_cost(sku, base_cost, cost_config)
    shipping = adjusted_cost - base_cost
    margin = get_margin(adjusted_cost)
    return [sku, round(base_cost * margin + shipping, DOLLAR_ROUND_DIGITS)]


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
