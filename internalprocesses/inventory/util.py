import re

from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.inventory.constants import *


def eval_conditions(condition_1: str,
                    condition_2: str,
                    condition_column: int,
                    data: list[str]) -> int:
    condition = data[condition_column]
    if eval(condition_1, {EVAL_CONDITION_VARIABLE_NAME: condition}):
        return 1
    elif eval(condition_2, {EVAL_CONDITION_VARIABLE_NAME: condition}):
        return 2
    return 0


def build_map_from_config(ftp: FTPConnection, value_column: int,
                          key_column: int, file_path: str = None,
                          dir_path=None) -> dict:
    map_ = {}
    collisions = {}
    try:
        for row in _get_file(ftp, dir_path, file_path):
            key = str(row[key_column]).upper()
            value = str(row[value_column]).upper()
            result = map_.get(key)
            if not result:
                map_[key] = value
            else:
                if collisions.get(key):
                    collisions[key].append(value)
                else:
                    collisions[key] = [result, value]
    except:
        print(key_column, value_column, file_path, dir_path)
    # Log collisions
    return map_


def get_adjusted_cost(inhouse_part_number: str, cost: float,
                      general_adjustment: int, steel_adjustment: int,
                      alloy_adjustment: int) -> float:
    material_code = str(inhouse_part_number)[:MATERIAL_CODE_END]
    if material_code == ALLOY_MATERIAL_CODE:
        cost += alloy_adjustment
    elif material_code == STEEL_MATERIAL_CODE:
        cost += steel_adjustment
    return cost + general_adjustment


def get_part_number(row: list[str], part_number_column: int,
                    sku_map: dict) -> str:
    raw_part_num = str(row[part_number_column]).upper()
    if sku_map:
        return sku_map.get(raw_part_num)
    if re.match(ROAD_READY_REPLICA_PATTERN, raw_part_num):
        return (raw_part_num[:MATERIAL_CODE_END] +
                raw_part_num[ROAD_READY_EXTRA_CHAR_END:])
    return raw_part_num


def get_inventory_key_and_min_qty(part_num: str, row: list[str] = None,
                                  condition_column: int = None,
                                  core_condition: str = None,
                                  finish_condition: str = None
                                  ) -> tuple[str | None, int | None]:
    if condition_column and core_condition and finish_condition and row:
        condition_result = eval_conditions(
            core_condition, finish_condition, condition_column, row
        )
        if condition_result == 1:
            return CORE_INVENTORY_KEY, CORE_MIN_QTY
        elif condition_result == 2:
            return CORE_INVENTORY_KEY, CORE_MIN_QTY
    try:
        if (re.match(FINISH_PATTERN, part_num) or
                re.match(REPLICA_PATTERN, part_num)):
            return FINISH_INVENTORY_KEY, FINISHED_MIN_QTY
        elif re.match(CORE_PATTERN, part_num):
            return CORE_INVENTORY_KEY, CORE_MIN_QTY
    except TypeError:
        # Log?
        pass
    return None, None


def include_row_item(exclusion_condition: str,
                     inclusion_condition: str,
                     inclusion_condition_column: int,
                     row: list[str]) -> bool:
    if (exclusion_condition and inclusion_condition and
            inclusion_condition_column):
        inclusion_result = eval_conditions(
            exclusion_condition, inclusion_condition,
            inclusion_condition_column, row
        )
        if inclusion_result == 2:
            return True
        else:
            return False
    return True


def add_to_inventory(inventory: dict, inventory_key: str, part_num: str,
                     vendor: str, qty: int, cost: float) -> None:
    if cost <= 0:
        return
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


def _get_file(ftp: FTPConnection, dir_path: str = None,
              file_path: str = None) -> list[list[str]]:
    if dir_path and not file_path:
        return ftp.get_directory_most_recent_file(dir_path, True)
    else:
        return ftp.get_file_as_list(file_path)


def add_vendor_inventory(ftp: FTPConnection, inventory: dict, vendor_name: str,
                         part_number_column: int, cost_column: int | None,
                         quantity_column: int, general_adjustment: int,
                         steel_adjustment: int, alloy_adjustment: int,
                         file_path: str = None, core_condition: str = None,
                         finish_condition: str = None,
                         classification_condition_column: int = None,
                         inclusion_condition: str = None,
                         exclusion_condition: str = None,
                         inclusion_condition_column: int = None,
                         sku_map: dict = None, cost_map: dict = None,
                         dir_path: str = None) -> None:
    for row in _get_file(ftp, dir_path, file_path):
        part_num = get_part_number(row, part_number_column, sku_map)
        inventory_key, min_qty = get_inventory_key_and_min_qty(
            part_num, row, classification_condition_column,
            core_condition, finish_condition
        )
        include = include_row_item(exclusion_condition, inclusion_condition,
                                   inclusion_condition_column, row)
        if not inventory_key or not include:
            continue
        if not part_num:
            # Log error
            continue
        try:
            if not cost_column and cost_map:
                cost_map_response = cost_map.get(part_num)
                if not cost_map_response:
                    # Log missing cost
                    continue
                cost, qty = float(cost_map_response), int(row[quantity_column])
            elif cost_column and not cost_map:
                cost, qty = float(row[cost_column]), int(row[quantity_column])
            else:
                raise Exception(f"{vendor_name} must have cost_column or " +
                                f"cost_map_config defined")
        except ValueError:
            continue
        cost = get_adjusted_cost(part_num, cost, general_adjustment,
                                 steel_adjustment, alloy_adjustment)
        if qty >= min_qty:
            add_to_inventory(
                inventory, inventory_key, part_num, vendor_name, qty, cost
            )


def add_inhouse_inventory(inventory, fishbowl_inventory_report):
    for row in fishbowl_inventory_report[1:]:
        raw_part_num, qty, avg_cost = [
            element.strip('"') for element in row.split(",")
        ]
        part_num = raw_part_num.upper()
        if re.match(FWW_CORE_PATTERN, part_num):
            inventory_key = CORE_INVENTORY_KEY
        else:
            inventory_key = FINISH_INVENTORY_KEY
        qty = int(float(qty))
        if avg_cost:
            avg_cost = round(float(avg_cost), ndigits=COST_ROUND_DIGITS)
        else:
            avg_cost = DEFAULT_AVG_COST
        add_to_inventory(inventory, inventory_key, part_num,
                         INHOUSE_VENDOR_KEY, qty, avg_cost)
