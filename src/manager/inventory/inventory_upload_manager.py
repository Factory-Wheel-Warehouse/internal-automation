from base64 import b64encode
from collections import defaultdict
from datetime import date
from io import BytesIO

import pandas as pd
from pandas import DataFrame

from src.dao.vendor_config_dao import VendorConfigDAO
from src.domain.inventory import Inventory
from src.domain.vendor import VendorConfig
from src.facade.fishbowl import FishbowlFacade
from src.facade.ftp.ftp_facade import FTPFacade
from src.facade.outlook import OutlookFacade
from src.manager.manager import Manager
from src.util.constants.credentials import FISHBOWL_CREDENTIALS
from src.util.constants.credentials import FTP_CREDENTIALS
from src.util.constants.credentials import OUTLOOK_CREDENTIALS
from src.util.constants.inventory import CORE_INVENTORY_KEY
from src.util.constants.inventory import FINISH_INVENTORY_KEY
from src.util.constants.inventory import MASTER_INVENTORY_PATH
from src.util.constants.inventory import MASTER_PRICING_MAP
from src.util.constants.inventory import PAINT_CODE_START


class InventoryUploadManager(Manager):
    _inventory: Inventory

    _ftp: FTPFacade = FTPFacade(**FTP_CREDENTIALS)
    _vendor_configs: list[VendorConfig] = VendorConfigDAO().get_all_items()
    _outlook: OutlookFacade = OutlookFacade(**OUTLOOK_CREDENTIALS)
    _HEADERS: list[str] = ["sku", "total_qty", "final_magento_qty", "avg_ht",
                           "walmart_ht", "list_price"]
    _VENDOR_SPECIFIC_HEADERS: list[str] = ["cost", "fin_qty", "core_qty",
                                           "combined_qty", "ht"]

    def __init__(self, fishbowl_facade: FishbowlFacade):
        super().__init__(fishbowl_facade)
        self._inventory = Inventory(self._vendor_configs, self._ftp,
                                    self._fishbowl_facade)

    def run(self):
        total_inv = self._build_total_inventory()
        df = self._populate_dataframe(total_inv,
                                      self._get_initial_dataframe())
        self._ftp.write_df_as_csv(MASTER_INVENTORY_PATH, df)
        self._email_master_inventory(df)

    def _email_master_inventory(self, df: DataFrame):
        file = BytesIO()
        df.to_csv(file, index=False)
        file.seek(0)
        date_ = date.today().isoformat()
        self._outlook.sendMail(to="danny@factorywheelwarehouse.com",
                               subject="Master Inventory Sheet",
                               body="File attached",
                               attachment=b64encode(file.read()).decode(),
                               attachmentName=f"fww_master_inventory_"
                                              f"{date_}.csv")

    def _get_initial_dataframe(self):
        vendor_headers = []
        for header in self._VENDOR_SPECIFIC_HEADERS:
            for vendor in self._vendor_configs:
                vendor_name = vendor.vendor_name.lower().replace(" ", "_")
                vendor_headers.append(f"{vendor_name}_{header}")
            vendor_headers.append(f"warehouse_{header}")
        headers = self._HEADERS[:2] + vendor_headers + self._HEADERS[2:]
        return DataFrame(columns=headers)

    def _get_formatted_row(self, sku: str, availability: dict, price: int,
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
                ht = self._get_sku_handling_time(sku, fin_qty > 2,
                                                 vendors.get(vendor))
                combined_qty = (fin_qty + core_qty)
                total_qty += combined_qty
                avg_ht = [avg_ht[0] + ht, avg_ht[1] + 1]
                for header in self._VENDOR_SPECIFIC_HEADERS:
                    formatted_vendor_name = vendor.lower().replace(" ", "_")
                    row[f"{formatted_vendor_name}_{header}"] = locals()[header]
        final_ht = round(avg_ht[0] / avg_ht[1]) if avg_ht[1] else 3
        row.update({"total_qty": total_qty,
                    "final_magento_qty": 3 if total_qty > 3 else total_qty,
                    "avg_ht": final_ht if final_ht <= 10 else 15,
                    "walmart_ht": self._get_walmart_handling_time(final_ht)})
        return row

    def _build_total_inventory(self) -> dict:
        total_inventory = {}
        finishes = defaultdict(list)
        for row in self._ftp.get_file_as_list(MASTER_INVENTORY_PATH):
            total_inventory[row[0]] = {}
            finishes[row[0][:PAINT_CODE_START]].append(row[0])
        finished_inv = self._inventory.inventory[FINISH_INVENTORY_KEY]
        for key, value in finished_inv.items():
            if key in total_inventory:
                total_inventory[key] = value
        core_inv = self._inventory.inventory[CORE_INVENTORY_KEY]
        for core, availability in core_inv.items():
            self._add_core_equivalents_to_total(total_inventory,
                                                finishes.get(core),
                                                availability)
        return total_inventory

    def _populate_dataframe(self, total_inventory: dict,
                            df: DataFrame) -> DataFrame:
        rows = []
        pricing = {r[0]: r[1] for r in self._ftp.get_file_as_list(
            MASTER_PRICING_MAP)}
        vendors = {vendor.vendor_name: vendor for vendor in
                   self._vendor_configs}
        for sku, availability in total_inventory.items():
            price = pricing.get(sku)
            rows.append(self._get_formatted_row(sku, availability, price,
                                                vendors))
        df = pd.concat([df, DataFrame(rows)], ignore_index=True)
        df.reset_index()
        return df

    @staticmethod
    def _add_core_equivalents_to_total(total_inventory: dict,
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

    @staticmethod
    def _get_sku_handling_time(sku: str, is_finished: bool,
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

    @staticmethod
    def _get_walmart_handling_time(ht: int):
        if ht <= 5:
            return 5
        elif ht <= 10:
            return 10
        return 3
