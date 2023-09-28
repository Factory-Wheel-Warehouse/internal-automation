from math import inf

from internalprocesses.inventory.util import *
from .constants import *
from .. import FishbowlClient
from ..ftpconnection.ftpConnection import FTPConnection
from ..vendor import VendorConfig


class Inventory:
    inventory = {CORE_INVENTORY_KEY: {}, FINISH_INVENTORY_KEY: {}}

    def __init__(self, vendor_configs: list[VendorConfig] | None,
                 ftp: FTPConnection | None,
                 fishbowl: FishbowlClient | None) -> None:
        if vendor_configs and ftp and fishbowl:
            add_inhouse_inventory(self.inventory, fishbowl.getPartsOnHand())
            price_map = self._get_price_map(ftp)
            for vendor in vendor_configs:
                sku_map = cost_map = None
                if vendor.sku_map_config:
                    sku_map = build_map_from_config(ftp, vendor.sku_map_config)
                if vendor.cost_map_config:
                    cost_map = build_map_from_config(ftp,
                                                     vendor.cost_map_config)
                add_vendor_inventory(ftp, self.inventory, vendor, sku_map,
                                     cost_map, price_map)

    def _decrement_inventory(self, inventory_key: str, part_number: str,
                             vendor: str, quantity: int) -> None:
        self.inventory[inventory_key][part_number][
            vendor][QUANTITY_INDEX] -= quantity
        if not self.inventory[inventory_key][part_number][
            vendor][QUANTITY_INDEX]:
            del self.inventory[inventory_key][part_number][vendor]
            if not self.inventory[inventory_key][part_number]:
                del self.inventory[inventory_key][part_number]

    @staticmethod
    def _get_price_map(ftp: FTPConnection):
        pricing_file = ftp.get_file_as_list(FTP_PRICING_FILE)
        return {r[0]: float(r[1]) for r in pricing_file}

    def _core_in_stock_inhouse(self, part_number: str, quantity: int) -> bool:
        core_search_value = get_core_search_value(part_number)
        if core_search_value:
            core_availability = self.inventory[CORE_INVENTORY_KEY].get(
                core_search_value
            )
            if core_availability:
                warehouse_availability = core_availability.get(
                    INHOUSE_VENDOR_KEY
                )
                if warehouse_availability:
                    warehouse_quantity = warehouse_availability[QUANTITY_INDEX]
                    if warehouse_quantity >= quantity:
                        self._decrement_inventory(CORE_INVENTORY_KEY,
                                                  core_search_value,
                                                  INHOUSE_VENDOR_KEY, quantity)
                        return True
        return False

    def handle_zero_cost(self, part_number: str, vendor: str) -> float:
        availability = self.inventory[FINISH_INVENTORY_KEY].get(part_number)
        if availability:
            vendor_availability = availability.get(vendor)
            if vendor_availability:
                return vendor_availability[COST_INDEX]
        return 0.0

    def get_cheapest_vendor(self, part_number: str,
                            quantity: int) -> tuple[str, float] | None:
        if self._core_in_stock_inhouse(part_number, quantity):
            return INHOUSE_VENDOR_KEY, 0.0
        search_order = [FINISH_INVENTORY_KEY, CORE_INVENTORY_KEY]
        for inventory_key in search_order:
            if inventory_key == CORE_INVENTORY_KEY:
                search = get_core_search_value(part_number)
                if not search:
                    pass
            else:
                search = part_number
            availability = self.inventory[inventory_key].get(search)
            if availability:
                min_ = inf
                min_vendor = None
                for vendor, stock_data in availability.items():
                    vendor_quantity, cost = stock_data
                    if cost == 0.0:
                        cost = self.handle_zero_cost(part_number, vendor)
                    if vendor_quantity >= quantity and cost < min_:
                        min_, min_vendor = cost, vendor
                if min_vendor:
                    self._decrement_inventory(inventory_key,
                                              search, min_vendor,
                                              quantity)
                    return min_vendor, min_
        return NO_VENDOR, 0.0
