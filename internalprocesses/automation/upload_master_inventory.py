from collections import defaultdict
from math import ceil

import pandas as pd

from pandas import DataFrame, read_excel

from internalprocesses.automation.constants import FTP_CREDENTIALS
from internalprocesses.aws.dynamodb import VendorConfigDAO
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.inventory import Inventory
from internalprocesses.inventory.constants import CORE_INVENTORY_KEY, \
    FINISH_INVENTORY_KEY, PAINT_CODE_START
from internalprocesses.vendor import VendorConfig

HEADERS = ["sku", "total_qty", "final_magento_qty", "avg_ht",
           "walmart_ht", "ebay_ht", "list_price", "list_on_elite"]
VENDOR_SPECIFIC_HEADERS = ["cost", "fin_qty", "core_qty", "combined_qty", "ht"]
FTP_SAVE_PATH = "/Magento_upload/source-file-2.csv"
FTP_PRICING_SHEET = "/Magento_upload/lkq_based_sku_pricing.csv"
MISSING_SKUS_FILE_PATH = "/Magento_upload/missing_skus.csv"

EBAY_HANDLING_TIMES = [1, 2, 3, 4, 5, 6, 7, 10, 15]
WALMART_HANDLING_TIMES = [5, 10]


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


def _get_skus_missing_data(ftp: FTPConnection):
    return ftp.get_file_as_list(MISSING_SKUS_FILE_PATH)


def build_total_inventory(inventory: Inventory, ftp: FTPConnection) -> dict:
    total_inventory = {}
    finishes = defaultdict(set)
    missing_skus = _get_skus_missing_data(ftp)
    for row in ftp.get_file_as_list(FTP_SAVE_PATH):
        total_inventory[row[0]] = {}
        paint_code = row[0][PAINT_CODE_START:]
        if paint_code[-1] != "N" and int(paint_code) < 95:
            finishes[row[0][:PAINT_CODE_START]].add(row[0].upper())
    for key, value in inventory.inventory[FINISH_INVENTORY_KEY].items():
        if key in total_inventory:
            total_inventory[key] = value
        else:
            if key not in missing_skus:
                missing_skus.append([key])
    for core, availability in inventory.inventory[CORE_INVENTORY_KEY].items():
        add_core_equivalents_to_total(total_inventory,
                                      finishes.get(core),
                                      availability)
    ftp.write_list_as_csv(MISSING_SKUS_FILE_PATH, missing_skus)
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
                       ftp: FTPConnection,
                       vendors: dict[str, VendorConfig]) -> DataFrame:
    pricing = {r[0]: r[1] for r in ftp.get_file_as_list(FTP_PRICING_SHEET)}
    rows = []
    for sku, availability in total_inventory.items():
        price = pricing.get(sku)
        rows.append(_get_formatted_row(sku, availability, price, vendors))
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
    row.update({"total_qty": total_qty,
                "final_magento_qty": 3 if total_qty > 3 else total_qty,
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


def upload_coast_based_pricing():
    vendor_configs: list[VendorConfig] = VendorConfigDAO().get_all_items()
    coast = None
    for vendor in vendor_configs:
        if vendor.vendor_name == "Coast To Coast":
            coast = vendor
    ftp = FTPConnection(**FTP_CREDENTIALS)
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
            margin = 1.35 if cost < 350 else 1.27
            price = round(ceil(cost * margin + shipping) - 0.01, 2)
            prices.append([sku, price])
    ftp.write_list_as_csv(FTP_PRICING_SHEET, prices)
    prices.sort(key=lambda x: x[1])
    print(f"Low: {prices[0][1]}\n"
          f"High: {prices[-1][1]}\n"
          f"Average: {sum([p[1] for p in prices]) / len(prices)}\n"
          f"Median: {prices[len(prices) // 2][1]}")
