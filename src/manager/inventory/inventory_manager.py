from base64 import b64encode
from datetime import date

import asyncio

from dependency_injector.wiring import inject

from src.dao.vendor_config_dao import VendorConfigDAO
from src.domain.inventory import Inventory
from src.facade.fishbowl import FishbowlFacade
from src.facade.outlook import OutlookFacade
from src.manager.manager import Manager
from src.facade.ftp.ftp_facade import FTPFacade
from src.util.constants.inventory import COAST_PRICING_SHEET
from src.util.constants.inventory import MASTER_INVENTORY_PATH
from src.util.constants.inventory import MASTER_PRICING_MAP
from src.util.inventory.master_inventory_util import build_total_inventory
from src.util.inventory.master_inventory_util import get_initial_dataframe
from src.util.inventory.master_inventory_util import populate_dataframe
from src.util.inventory.pricing_util import get_list_price
from src.util.inventory.pricing_util import get_sku_map
from src.util.inventory.pricing_util import get_stats


class InventoryManager(Manager):
    _ftp: FTPFacade = FTPFacade()
    _vendor_config_dao: VendorConfigDAO = VendorConfigDAO()
    _fishbowl_facade: FishbowlFacade = FishbowlFacade()
    _inventory: Inventory = Inventory()
    _outlook_facade: OutlookFacade = OutlookFacade()

    @property
    def endpoint(self):
        return "/inventory/"

    @Manager.action
    def upload(self):
        self._ftp.start()
        self._fishbowl_facade.start()
        self._outlook_facade.login()
        self._inventory.build(self._ftp, self._fishbowl_facade)
        vendor_configs = self._vendor_config_dao.get_all_items()
        total_inv = build_total_inventory(self._ftp, self._inventory)
        df = populate_dataframe(self._ftp, vendor_configs, total_inv,
                                get_initial_dataframe(vendor_configs))
        self._ftp.write_df_as_csv(MASTER_INVENTORY_PATH, df)
        self._ftp.close()
        self._fishbowl_facade.close()
        self.email()

    @Manager.action
    @Manager.asynchronous()
    def email(self):
        self._ftp.start()
        self._outlook_facade.login()
        file = self._ftp.get_file_as_binary(MASTER_INVENTORY_PATH)
        encoded_file = b64encode(file.read()).decode()
        date_ = date.today().isoformat()
        file_name = f"fww_master_inventory_{date_}.csv"
        self._outlook_facade.sendMail(to="sales@factorywheelwarehouse.com",
                                      subject="Master Inventory Sheet",
                                      body="File attached",
                                      attachment=encoded_file,
                                      attachmentName=file_name)
        self._ftp.close()

    @Manager.action
    @Manager.asynchronous()
    def pricing(self):
        self._ftp.start()
        coast_vendor_config = self._vendor_config_dao.get_item("Coast To "
                                                               "Coast")
        prices = []
        map_ = get_sku_map(self._ftp, coast_vendor_config)
        rows = self._ftp.get_file_as_list(COAST_PRICING_SHEET)
        for row in rows:
            part_num, base_cost = row
            sku = map_.get(part_num)
            if sku:
                pricing = get_list_price(coast_vendor_config, sku, base_cost)
                prices.append(pricing)
        self._ftp.write_list_as_csv(MASTER_PRICING_MAP, prices)
        self._ftp.close()

        #
        # TODO: log -> print(get_stats(sorted(prices, key=lambda x: x[1])))
