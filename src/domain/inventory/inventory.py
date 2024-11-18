from math import inf

from src.dao import VendorConfigDAO
from src.domain.inventory.inventory_entry import InventoryEntry
from src.domain.inventory.vendor_availability import VendorAvailability
from src.facade.fishbowl import FishbowlFacade
from src.facade.ftp.ftp_facade import FTPFacade
from src.util.constants.inventory import CORE_INVENTORY_KEY
from src.util.constants.inventory import COST_INDEX
from src.util.constants.inventory import FINISH_INVENTORY_KEY
from src.util.constants.inventory import INHOUSE_VENDOR_KEY
from src.util.constants.inventory import NO_VENDOR
from src.util.constants.inventory import PAINT_CODE_START
from src.util.constants.inventory import QUANTITY_INDEX
from src.util.inventory.inventory_util import add_inhouse_inventory
from src.util.inventory.inventory_util import add_vendor_inventory
from src.util.inventory.inventory_util import build_map_from_config
from src.util.inventory.inventory_util import get_core_search_value
from src.util.inventory.inventory_util import get_price_map


class Inventory:

    def __init__(self):
        self._vendor_configs = VendorConfigDAO().get_all_items()
        self.inventory = {CORE_INVENTORY_KEY: {},
                          FINISH_INVENTORY_KEY: {}}

    def build(self, ftp: FTPFacade, fishbowl: FishbowlFacade):
        add_inhouse_inventory(self.inventory, fishbowl.getPartsOnHand())
        price_map = get_price_map(ftp)
        for vendor in self._vendor_configs:
            sku_map = cost_map = None
            if vendor.sku_map_config:
                sku_map = build_map_from_config(ftp,
                                                vendor.sku_map_config)
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
                            quantity: int) -> tuple[str, float, str] | None:
        if self._core_in_stock_inhouse(part_number, quantity):
            return INHOUSE_VENDOR_KEY, 0.0, CORE_INVENTORY_KEY
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
                    vendor_quantity, cost, *_ = stock_data
                    if cost == 0.0:
                        cost = self.handle_zero_cost(part_number, vendor)
                    if vendor_quantity >= quantity and cost < min_:
                        min_, min_vendor = cost, vendor
                if min_vendor:
                    self._decrement_inventory(inventory_key,
                                              search, min_vendor,
                                              quantity)
                    return min_vendor, min_, inventory_key
        return NO_VENDOR, 0.0, ""

    def convert_to_entries(self):
        vendor_map = {v.vendor_name: v for v in self._vendor_configs}
        inventory_as_entries = []
        for finish_status in self.inventory.keys():
            for sku, availability in self.inventory[finish_status].items():
                vendor_availability = []
                for vendor, stock_data in availability.items():
                    quantity, cost, *_ = stock_data
                    if vendor_map.get(vendor):
                        ht = vendor_map[vendor].get_handling_time(
                            sku, finish_status.upper())
                    else:
                        if finish_status == FINISH_INVENTORY_KEY:
                            ht = 1
                        else:
                            ht = 15 if "80" in sku[PAINT_CODE_START:] else 3
                    vendor_availability.append(
                        VendorAvailability(vendor, quantity, cost, ht))
                inventory_as_entries.append(
                    InventoryEntry(sku, finish_status,
                                   vendor_availability))
        return inventory_as_entries
