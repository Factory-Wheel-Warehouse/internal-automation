import os
from math import inf

from internalprocesses.inventory.util import *
from .constants import *
from .. import FishbowlClient
from ..ftpconnection.ftpConnection import FTPConnection
from ..vendor import VendorConfig


class Inventory:
    def __init__(self, vendor_configs: list[VendorConfig],
                 ftp: FTPConnection, fishbowl: FishbowlClient) -> None:
        self.inventory = {CORE_INVENTORY_KEY: {}, FINISH_INVENTORY_KEY: {}}
        add_inhouse_inventory(self.inventory, fishbowl.getPartsOnHand())
        for vendor in vendor_configs:
            sku_map = cost_map = None
            if hasattr(vendor, SKU_MAP_CONFIG_ATTRIBUTE):
                sku_map = build_map_from_config(
                    ftp, **vars(vendor.sku_map_config))
            if hasattr(vendor, COST_MAP_CONFIG_ATTRIBUTE):
                cost_map = build_map_from_config(
                    ftp, **vars(vendor.cost_map_config))
            add_vendor_inventory(ftp, self.inventory, vendor.vendor_name,
                                 sku_map=sku_map, cost_map=cost_map,
                                 **vars(vendor.inventory_file_config),
                                 **vars(vendor.cost_adjustment_config),
                                 **vars(vendor.classification_config))

    def _decrement_inventory(self, inventory_key: str, part_number: str,
                             vendor: str, quantity: int) -> None:
        self.inventory[inventory_key][part_number][
            vendor][QUANTITY_INDEX] -= quantity
        if not self.inventory[inventory_key][part_number][
            vendor][QUANTITY_INDEX]:
            del self.inventory[inventory_key][part_number][vendor]
            if not self.inventory[inventory_key][part_number]:
                del self.inventory[inventory_key][part_number]

    def get_availability(self, part_number: str) -> list[dict]:
        results = []
        for key in self.inventory.keys():
            for part, stock in self.inventory[key].items():
                if part_number in part:
                    results.append({part: stock})
        return results

    # Public get cheapest vendor

    def _core_in_stock_inhouse(self, part_number: str, quantity: int) -> bool:
        if len(part_number) > PAINT_CODE_START:
            paint_code = int(part_number[PAINT_CODE_START: PAINT_CODE_END])
        else:
            paint_code = 0
        part_number_copy = str(part_number)[:PAINT_CODE_START]
        if not re.match(REPLICA_PATTERN, part_number):
            core_availability = self.inventory[CORE_INVENTORY_KEY].get(
                part_number_copy
            )
            if core_availability:
                warehouse_availability = core_availability.get(
                    INHOUSE_VENDOR_KEY
                )
                if (warehouse_availability and
                        paint_code < POLISHED_PAINT_CODE_START):
                    warehouse_quantity = warehouse_availability[QUANTITY_INDEX]
                    if warehouse_quantity >= quantity:
                        self._decrement_inventory(CORE_INVENTORY_KEY,
                                                  part_number_copy,
                                                  INHOUSE_VENDOR_KEY, quantity)
                    return True
        return False

    def get_cheapest_vendor(self, part_number: str,
                            quantity: int) -> str | None:
        if self._core_in_stock_inhouse(part_number, quantity):
            return INHOUSE_VENDOR_KEY
        search_order = [FINISH_INVENTORY_KEY, CORE_INVENTORY_KEY]
        for inventory_key in search_order:
            availability = self.inventory[inventory_key].get(part_number)
            if availability:
                min_ = inf
                min_vendor = None
                for vendor, stock_data in availability.items():
                    vendor_quantity, cost = stock_data
                    if vendor_quantity >= quantity and cost < min_:
                        min_, min_vendor = cost, vendor
                if min_vendor:
                    self._decrement_inventory(inventory_key,
                                              part_number, min_vendor,
                                              quantity)
                    return min_vendor
