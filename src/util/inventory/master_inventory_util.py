from collections import defaultdict

import pandas as pd
from pandas import DataFrame

from src.domain.inventory import Inventory
from src.domain.vendor import VendorConfig
from src.facade.ftp.ftp_facade import FTPFacade
from src.util.constants.inventory import CORE_INVENTORY_KEY
from src.util.constants.inventory import FINISH_INVENTORY_KEY
from src.util.constants.inventory import HEADERS
from src.util.constants.inventory import MASTER_INVENTORY_PATH
from src.util.constants.inventory import MASTER_PRICING_MAP

from src.util.constants.inventory import PAINT_CODE_START
from src.util.constants.inventory import VENDOR_SPECIFIC_HEADERS


def get_initial_dataframe(vendor_configs: list[VendorConfig]):
    vendor_headers = []
    for header in VENDOR_SPECIFIC_HEADERS:
        for vendor in vendor_configs:
            vendor_name = vendor.vendor_name.lower().replace(" ", "_")
            vendor_headers.append(f"{vendor_name}_{header}")
        vendor_headers.append(f"warehouse_{header}")
    headers = HEADERS[:2] + vendor_headers + HEADERS[2:]
    return DataFrame(columns=headers)


def get_formatted_row(sku: str, availability: dict, price: int,
                      vendors: dict[str, VendorConfig]) -> dict:
    price = price if price else 5000
    row = {"sku": sku, "list_price": price}
    total_qty, avg_ht, max_cost = 0, [0, 0], 0
    if total_qty > 0:
        print(total_qty)
    if price < 5000:
        for vendor, detailed_availability in availability.items():
            fin_qty, cost, *extended_unpacking = detailed_availability
            core_qty = extended_unpacking[0] if extended_unpacking else 0
            ht = get_sku_handling_time(sku, fin_qty > 2,
                                       vendors.get(vendor))
            combined_qty = (fin_qty + core_qty)
            total_qty += combined_qty
            avg_ht = [avg_ht[0] + ht, avg_ht[1] + 1]
            for header in VENDOR_SPECIFIC_HEADERS:
                formatted_vendor_name = vendor.lower().replace(" ", "_")
                row[f"{formatted_vendor_name}_{header}"] = locals()[header]
    final_ht = round(avg_ht[0] / avg_ht[1]) if avg_ht[1] else 3
    row.update({"total_qty": total_qty,
                "final_magento_qty": 3 if total_qty > 3 else total_qty,
                "avg_ht": final_ht if final_ht <= 10 else 15,
                "walmart_ht": get_walmart_handling_time(final_ht)})
    return row


def build_total_inventory(ftp: FTPFacade, inventory: Inventory) -> dict:
    total_inventory = {}
    finishes = defaultdict(list)
    for row in ftp.get_file_as_list(MASTER_INVENTORY_PATH):
        total_inventory[row[0]] = {}
        finishes[row[0][:PAINT_CODE_START]].append(row[0])
    finished_inv = inventory.inventory[FINISH_INVENTORY_KEY]
    for key, value in finished_inv.items():
        if key in total_inventory:
            total_inventory[key] = value
    core_inv = inventory.inventory[CORE_INVENTORY_KEY]
    for core, availability in core_inv.items():
        add_core_equivalents_to_total(total_inventory,
                                      finishes.get(core),
                                      availability)
    return total_inventory


def populate_dataframe(ftp: FTPFacade, vendor_configs: list[VendorConfig],
                       total_inventory: dict, df: DataFrame) -> DataFrame:
    rows = []
    pricing = {r[0]: r[1] for r in ftp.get_file_as_list(
        MASTER_PRICING_MAP)}
    vendors = {vendor.vendor_name: vendor for vendor in
               vendor_configs}
    for sku, availability in total_inventory.items():
        price = pricing.get(sku)
        rows.append(get_formatted_row(sku, availability, price,
                                      vendors))
    df = pd.concat([df, DataFrame(rows)], ignore_index=True)
    df.reset_index()
    return df


def add_core_equivalents_to_total(total_inventory: dict,
                                  finishes: list[str],
                                  core_availability: dict) -> None:
    if finishes:
        for core_vendor, vendor_details in core_availability.items():
            qty, cost = vendor_details
            for finish in finishes:
                if total_inventory.get(finish):
                    if total_inventory[finish].get(core_vendor):
                        total_inventory[finish][core_vendor].append(qty)
                    else:
                        total_inventory[finish][core_vendor] = [0, cost,
                                                                qty]


def get_sku_handling_time(sku: str, is_finished: bool,
                          vendor: VendorConfig | None) -> int:
    paint_code = sku[PAINT_CODE_START:][:2]
    status = "FINISHED" if is_finished else "CORE"
    if vendor and vendor.handling_time_config:
        return vendor.get_handling_time(paint_code, status)
    paint_code = int(paint_code[:2])
    ht_values = {
        "finished": 1,
        "core": 15 if paint_code >= 80 else 2
    }
    return ht_values["finished"] if is_finished else ht_values["core"]


def get_walmart_handling_time(ht: int):
    if ht <= 5:
        return 5
    elif ht <= 10:
        return 10
    return 3
