import logging
from collections import defaultdict
from math import ceil

import pandas as pd
from pandas import DataFrame
from pandas import read_excel
from pandas.errors import EmptyDataError

from src.dao.vendor_config_dao import VendorConfigDAO
from src.domain.inventory.inventory import Inventory
from src.domain.vendor import VendorConfig
from src.facade.ftp.ftp_facade import FTPFacade
from src.util.constants.inventory import CORE_INVENTORY_KEY
from src.util.constants.inventory import EBAY_HANDLING_TIMES
from src.util.constants.inventory import FINISH_INVENTORY_KEY
from src.util.constants.inventory import HIGH_COST_MARGIN
from src.util.constants.inventory import HIGH_COST_THRESHOLD
from src.util.constants.inventory import LOW_COST_MARGIN
from src.util.constants.inventory import MASTER_PRICING_PATH
from src.util.constants.inventory import LISTABLE_SKUS_PATH
from src.util.constants.inventory import HEADERS
from src.util.constants.inventory import MAX_SKU_LISTING_QTY
from src.util.constants.inventory import MISSING_SKUS_PATH

from src.util.constants.inventory import PAINT_CODE_START
from src.util.constants.inventory import PRICE_BUFFER
from src.util.constants.inventory import VENDOR_SPECIFIC_HEADERS
from src.util.constants.inventory import WALMART_HANDLING_TIMES


def get_initial_dataframe(vendor_configs: list[VendorConfig]):
    # limit total to five
    # walmart ht must be 5 or 10
    vendor_headers = []
    for header in VENDOR_SPECIFIC_HEADERS:
        for vendor in vendor_configs:
            vendor_name = vendor.vendor_name.lower().replace(" ", "_")
            vendor_headers.append(f"{vendor_name}_{header}")
        vendor_headers.append(f"warehouse_{header}")
    headers = HEADERS[:2] + vendor_headers + HEADERS[2:]
    return DataFrame(columns=headers)


def _get_skus_missing_data(ftp: FTPFacade):
    try:
        return ftp.get_file_as_list(MISSING_SKUS_PATH)
    except EmptyDataError:
        return []


def build_total_inventory(inventory: Inventory, ftp: FTPFacade) -> dict:
    total_inventory = {}
    finishes = defaultdict(set)
    missing_skus = _get_skus_missing_data(ftp)
    for row in ftp.get_file_as_list(LISTABLE_SKUS_PATH):
        try:
            total_inventory[row[0]] = {}
            paint_code = int(row[0][PAINT_CODE_START: PAINT_CODE_START + 2])
            if "N" not in row[0] and not (paint_code in [85, 86]
                                          or paint_code >= 90):
                finishes[row[0][:PAINT_CODE_START]].add(row[0].upper())
        except ValueError as e:
            logging.error(
                f"Exception {e} thrown during inventory creation",
                exc_info=e.__traceback__
            )
            continue
    for key, value in inventory.inventory[FINISH_INVENTORY_KEY].items():
        if key in total_inventory:
            total_inventory[key] = value
        else:
            if [key] not in missing_skus:
                missing_skus.append([key])
    for core, availability in inventory.inventory[CORE_INVENTORY_KEY].items():
        add_core_equivalents_to_total(total_inventory,
                                      finishes.get(core),
                                      availability)
    ftp.write_list_as_csv(MISSING_SKUS_PATH, missing_skus)
    return total_inventory


def add_core_equivalents_to_total(total_inventory: dict, finishes: set[str],
                                  core_availability: dict) -> None:
    if not finishes:
        return
    for core_vendor, vendor_details in core_availability.items():
        qty, cost = vendor_details
        for finish in finishes:
            if total_inventory[finish].get(core_vendor):
                if len(total_inventory[finish][core_vendor]) < 3:
                    total_inventory[finish][core_vendor].append(qty)
                else:
                    total_inventory[finish][core_vendor][2] += qty
            else:
                total_inventory[finish][core_vendor] = [0, cost, qty]


def populate_dataframe(total_inventory: dict, df: DataFrame,
                       ftp: FTPFacade,
                       vendors: list[VendorConfig]) -> DataFrame:
    pricing = {r[0]: r[1] for r in ftp.get_file_as_list(MASTER_PRICING_PATH)}
    vendor_map = {vendor.vendor_name: vendor for vendor in vendors}
    rows = []
    for sku, availability in total_inventory.items():
        price = pricing.get(sku)
        rows.append(_get_formatted_row(sku, availability, price, vendor_map))
    df = pd.concat([df, DataFrame(rows)], ignore_index=True)
    df.reset_index()
    return df


def _get_sku_handling_time(sku: str, is_finished: bool,
                           vendor: VendorConfig | None) -> int:
    paint_code = sku[PAINT_CODE_START:][:2]
    status = "FINISHED" if is_finished else "CORE"
    if vendor and vendor.handling_time_config:
        return vendor.get_handling_time(paint_code, status)
    paint_code = int(paint_code[:2])
    ht_values = {
        "finished": 1,
        "core": 15 if paint_code >= 80 else 3
    }
    return ht_values["finished"] if is_finished else ht_values["core"]


def _get_acceptable_ht(ht: int, good_hts: list[int]):
    for good_ht in good_hts:
        if ht <= good_ht:
            return good_ht
    return good_hts[-1] + 1  # Return max acceptable ht plus one by default


def _get_formatted_row(sku: str, availability: dict, price: float,
                       vendors: dict[str, VendorConfig]) -> dict:
    price = price if price else 100.0
    row = {"sku": sku, "list_price": price}
    total_qty, avg_ht, max_cost = 0, [0, 0], 0
    list_on_elite = False
    if price != 100.0:
        for vendor, detailed_availability in availability.items():
            vendor_config = vendors.get(vendor)
            fin_qty, cost, *extended_unpacking = detailed_availability
            core_qty = extended_unpacking[0] if extended_unpacking else 0
            combined_qty = _get_combined_qty(fin_qty, core_qty, vendor_config)
            is_finished = fin_qty >= 2 or (core_qty == 0 and fin_qty > 0)
            ht = _get_sku_handling_time(sku, is_finished, vendor_config)
            if vendor == "Warehouse" and combined_qty > 0:
                list_on_elite = True
                total_qty = combined_qty
            if not list_on_elite:
                total_qty += combined_qty
            avg_ht = [avg_ht[0] + ht, avg_ht[1] + 1]
            for header in VENDOR_SPECIFIC_HEADERS:
                formatted_vendor_name = vendor.lower().replace(" ", "_")
                row[f"{formatted_vendor_name}_{header}"] = locals()[header]
    final_ht = round(avg_ht[0] / avg_ht[1]) if avg_ht[1] else 3
    final_magento_qty = min(total_qty, MAX_SKU_LISTING_QTY)

    row.update({"total_qty": total_qty,
                "final_magento_qty": final_magento_qty,
                "avg_ht": final_ht if final_ht <= 10 else 15,
                "ebay_ht": _get_acceptable_ht(final_ht, EBAY_HANDLING_TIMES),
                "walmart_ht": _get_acceptable_ht(final_ht,
                                                 WALMART_HANDLING_TIMES),
                "list_on_elite": list_on_elite})
    return row


def _get_combined_qty(fin_qty: int, core_qty: int,
                      vendor: VendorConfig | None) -> int:
    if vendor:
        qty_deduction = vendor.inventory_file_config.quantity_deduction
        if qty_deduction:
            adjusted_cost = fin_qty + core_qty - qty_deduction
            return adjusted_cost if adjusted_cost > 0 else 0
    return fin_qty + core_qty


def _get_margin(cost: float) -> float:
    return LOW_COST_MARGIN if cost < HIGH_COST_THRESHOLD else HIGH_COST_MARGIN


def _get_price(cost: float, shipping_cost: float) -> float:
    margin = _get_margin(cost)
    corrected_raw_price = (cost * margin) + shipping_cost + PRICE_BUFFER
    return round(ceil(corrected_raw_price) - 0.01, 2)


def upload_coast_based_pricing():
    coast: VendorConfig = VendorConfigDAO().get_item("Coast To Coast")
    ftp = FTPFacade()
    ftp.start()
    map_file = ftp.get_file_as_list(coast.sku_map_config.file_path)
    map_ = {}
    for row in map_file:
        vendor_part_col = coast.sku_map_config.vendor_part_number_column
        inhouse_part_col = coast.sku_map_config.inhouse_part_number_column
        map_[row[vendor_part_col]] = row[inhouse_part_col]
    rows = read_excel(r"C:\Users\danny\Documents\lkq_pricing.xlsx").values
    prices = []
    for row in rows:
        part_num, cost = row
        sku = map_.get(part_num)
        if sku:
            shipping = 17.5 if sku.startswith("STL") else 12.5
            price = _get_price(cost, shipping)
            prices.append([sku, price])
    ftp.write_list_as_csv(MASTER_PRICING_PATH, prices)
    prices.sort(key=lambda x: x[1])
    logging.info(f"Low: {prices[0][1]}\n"
                 f"High: {prices[-1][1]}\n"
                 f"Average: {sum([p[1] for p in prices]) / len(prices)}\n"
                 f"Median: {prices[len(prices) // 2][1]}")


if __name__ == "__main__":
    upload_coast_based_pricing()
