import math
import re

from src.domain.vendor import VendorConfig
from src.domain.vendor.classification_config import ClassificationConfig
from src.domain.vendor.cost_config import CostConfig
from src.domain.vendor.cost_map_config import CostMapConfig
from src.domain.vendor.inclusion_config import InclusionConfig
from src.domain.vendor.inventory_file_config import InventoryFileConfig
from src.domain.vendor.sku_map_config import SkuMapConfig
from src.facade.ftp.ftp_facade import FTPFacade
from src.util.constants.inventory import ALLOY_MATERIAL_CODE
from src.util.constants.inventory import CORE_INVENTORY_KEY
from src.util.constants.inventory import CORE_MIN_QTY
from src.util.constants.inventory import CORE_PATTERN
from src.util.constants.inventory import EVAL_CONDITION_VARIABLE_NAME
from src.util.constants.inventory import FINISHED_MIN_QTY
from src.util.constants.inventory import FINISH_INVENTORY_KEY
from src.util.constants.inventory import FINISH_PATTERN
from src.util.constants.inventory import FWW_CORE_PATTERN
from src.util.constants.inventory import INHOUSE_VENDOR_KEY
from src.util.constants.inventory import MASTER_PRICING_PATH
from src.util.constants.inventory import MATERIAL_CODE_END
from src.util.constants.inventory import MINIMUM_MARGIN
from src.util.constants.inventory import PAINT_CODE_END
from src.util.constants.inventory import PAINT_CODE_START
from src.util.constants.inventory import POLISHED_PAINT_CODE_START
from src.util.constants.inventory import QUANTITY_INDEX
from src.util.constants.inventory import REPLICA_MIN_QTY
from src.util.constants.inventory import REPLICA_PATTERN
from src.util.constants.inventory import ROAD_READY_EXTRA_CHAR_END
from src.util.constants.inventory import ROAD_READY_FINISH_PATTERN
from src.util.constants.inventory import STEEL_MATERIAL_CODE


def _eval_conditions(condition_1: str,
                     condition_2: str,
                     condition_column: int,
                     data: list[str]) -> int:  # TODO: build in to class?
    condition = data[condition_column]
    if condition_1 and eval(
            condition_1, {EVAL_CONDITION_VARIABLE_NAME: condition}):
        return 1
    elif condition_2 and eval(
            condition_2, {EVAL_CONDITION_VARIABLE_NAME: condition}):
        return 2
    return 0


def build_map_from_config(ftp: FTPFacade,
                          config: SkuMapConfig | CostMapConfig) -> dict:
    map_, collisions = {}, {}
    for row in _get_file(ftp, config):
        key = str(row[config.key_column]).upper()
        value = str(row[config.value_column]).upper()
        result = map_.get(key)
        if not result:
            map_[key] = value
        else:
            if collisions.get(key) and value not in collisions[key]:
                collisions[key].add(value)
            else:
                collisions[key] = {result, value}
    return map_


def get_adjusted_cost(inhouse_part_number: str, cost: float,
                      config: CostConfig | None) -> float:
    if cost == 0.0:
        return 0.0
    if config:
        material_code = str(inhouse_part_number)[:MATERIAL_CODE_END]
        if material_code == ALLOY_MATERIAL_CODE:
            cost += config.alloy_adjustment
        elif material_code == STEEL_MATERIAL_CODE:
            cost += config.steel_adjustment
        if config.ucode_adjustment:
            ucode = inhouse_part_number[PAINT_CODE_START:]
            cost += config.ucode_adjustment.get(ucode)
        return cost + config.general_adjustment
    return cost


def _get_part_number(row: list[str], part_number_column: int,
                     sku_map: dict) -> str:
    raw_part_num = str(row[part_number_column]).upper()
    if sku_map:
        return sku_map.get(raw_part_num)
    if re.match(ROAD_READY_FINISH_PATTERN, raw_part_num):
        return (raw_part_num[:MATERIAL_CODE_END] +
                raw_part_num[ROAD_READY_EXTRA_CHAR_END:])
    if (re.match(FINISH_PATTERN, raw_part_num) or
            re.match(CORE_PATTERN, raw_part_num) or
            re.match(REPLICA_PATTERN, raw_part_num)):
        return raw_part_num


def _get_inventory_key_and_min_qty(part_num: str, row: list[str],
                                   config: ClassificationConfig | None
                                   ) -> tuple[str | None, int | None]:
    if config:
        condition_result = _eval_conditions(
            config.core_condition, config.finish_condition,
            config.classification_condition_column, row
        )
        if condition_result == 1:
            return CORE_INVENTORY_KEY, CORE_MIN_QTY
        elif condition_result == 2:
            return FINISH_INVENTORY_KEY, FINISHED_MIN_QTY
    if re.match(FINISH_PATTERN, part_num):
        return FINISH_INVENTORY_KEY, FINISHED_MIN_QTY
    elif re.match(CORE_PATTERN, part_num):
        return CORE_INVENTORY_KEY, CORE_MIN_QTY
    elif re.match(REPLICA_PATTERN, part_num):
        return FINISH_INVENTORY_KEY, REPLICA_MIN_QTY
    return None, None


def _get_inhouse_paint_code(inhouse_part_num: str) -> int:
    if len(inhouse_part_num) > PAINT_CODE_START:
        return int(inhouse_part_num[PAINT_CODE_START: PAINT_CODE_END])
    else:
        return -1


def include_row_item(row: list[str], config: InclusionConfig | None,
                     cost: float, price: float, part_num: str) -> bool:
    if math.isnan(cost):
        return False
    if cost and cost * MINIMUM_MARGIN > price:
        return False
    paint_code = _get_inhouse_paint_code(part_num)
    if paint_code >= 95 or paint_code in [85, 86]:
        return False
    if config:
        inclusion_result = _eval_conditions(
            config.exclusion_condition, config.inclusion_condition,
            config.inclusion_condition_column, row
        )
        if inclusion_result == 2:
            return True
        else:
            return False
    return True


def _add_to_inventory(inventory: dict, inventory_key: str, part_num: str,
                      vendor: str, qty: int, cost: float) -> None:
    if (len(part_num) > PAINT_CODE_START and
            inventory_key == CORE_INVENTORY_KEY):
        part_num = part_num[:PAINT_CODE_START]
    if part_num not in inventory[inventory_key]:
        inventory[inventory_key][part_num] = {vendor: [qty, cost]}
    else:
        if vendor not in inventory[inventory_key][part_num]:
            inventory[inventory_key][part_num][vendor] = [qty, cost]
        else:
            inventory[inventory_key][part_num][vendor][QUANTITY_INDEX] += qty


def _get_file(ftp: FTPFacade,
              config: InventoryFileConfig | SkuMapConfig | CostMapConfig,
              **kwargs) -> list[list[str]]:
    if config.dir_path:
        return ftp.get_directory_most_recent_file(config.dir_path,
                                                  config.encoding, True)
    else:
        return ftp.get_file_as_list(config.file_path, config.encoding)


def _get_part_cost(cost_map: dict, part_num: str, row: list,
                   vendor: VendorConfig) -> float:
    if cost_map:
        cost_map_response = cost_map.get(part_num)
        if not cost_map_response:
            return -1
        cost = float(cost_map_response)
    else:
        try:
            cost = float(row[vendor.inventory_file_config.cost_column])
        except ValueError:
            return -1  # Catch NaN
    return cost


def _get_qty(row: list, vendor: VendorConfig) -> int:
    try:
        qty = int(row[vendor.inventory_file_config.quantity_column])
    except ValueError:
        return -1  # Catch NaN
    return qty


def add_vendor_inventory(ftp: FTPFacade, inventory: dict,
                         vendor: VendorConfig, sku_map: dict,
                         cost_map: dict, price_map: dict) -> None:
    for row in _get_file(ftp, vendor.inventory_file_config):
        part_number_column = vendor.inventory_file_config.part_number_column
        part_num = _get_part_number(row, part_number_column, sku_map)
        if part_num:
            inventory_key, min_qty = _get_inventory_key_and_min_qty(
                part_num, row, vendor.classification_config)
            price = price_map.get(part_num) if price_map.get(part_num) else -1
            cost = _get_part_cost(cost_map, part_num, row, vendor)
            cost = get_adjusted_cost(part_num, cost,
                                     vendor.cost_adjustment_config)
            include = include_row_item(row, vendor.inclusion_config,
                                       cost, price, part_num)
            if inventory_key and include:
                qty = _get_qty(row, vendor)
                if qty >= min_qty:
                    _add_to_inventory(inventory, inventory_key, part_num,
                                      vendor.vendor_name, qty, cost)


def add_inhouse_inventory(inventory, fishbowl_inventory_report):
    for row in fishbowl_inventory_report[1:]:
        raw_part_num, qty, avg_cost = [
            element.strip('"').strip() for element in row.split(",")
        ]
        part_num = raw_part_num.upper()
        inventory_key = None
        if re.match(FWW_CORE_PATTERN, part_num):
            inventory_key = CORE_INVENTORY_KEY
        elif re.match(FINISH_PATTERN, part_num):
            inventory_key = FINISH_INVENTORY_KEY
        qty = int(float(qty))
        # Always use cost of zero to prioritize inhouse assignments
        if inventory_key and inventory_key == CORE_INVENTORY_KEY:
            _add_to_inventory(inventory, inventory_key, part_num,
                              INHOUSE_VENDOR_KEY, qty, 0.0)


def get_core_search_value(part_num: str) -> str | None:
    is_replica = re.match(REPLICA_PATTERN, part_num)
    is_polished = _get_inhouse_paint_code(part_num) > POLISHED_PAINT_CODE_START
    if not (is_replica or is_polished):
        return str(part_num)[:PAINT_CODE_START]
    return None


def get_price_map(ftp: FTPFacade):
    pricing_file = ftp.get_file_as_list(MASTER_PRICING_PATH)
    return {r[0]: float(r[1]) for r in pricing_file}
