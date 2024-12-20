from src.dao.inventory_dao import InventoryDAO
from src.dao.vendor_config_dao import VendorConfigDAO
from src.domain.inventory.inventory import Inventory
from src.facade.fishbowl import FishbowlFacade
from src.facade.ftp.ftp_facade import FTPFacade
from src.manager.manager import Manager
from src.util.constants.inventory import COAST_PRICING_PATH
from src.util.constants.inventory import MASTER_INVENTORY_PATH
from src.util.constants.inventory import MASTER_PRICING_PATH
from src.util.inventory.inventory_util import get_adjusted_cost
from src.util.inventory.master_inventory_util import build_total_inventory
from src.util.inventory.master_inventory_util import get_initial_dataframe
from src.util.inventory.master_inventory_util import populate_dataframe
from src.util.inventory.pricing_util import get_list_price
from src.util.inventory.pricing_util import get_sku_map
from src.util.logging import log_exceptions


class InventoryUploadManager(Manager):
    _ftp: FTPFacade = FTPFacade()
    _vendor_config_dao: VendorConfigDAO = VendorConfigDAO()
    _inventory_dao: InventoryDAO = InventoryDAO()
    _fishbowl_facade: FishbowlFacade = FishbowlFacade()
    _inventory: Inventory = Inventory()

    @property
    def endpoint(self):
        return "upload"

    @Manager.action
    @Manager.asynchronous()
    @log_exceptions
    def ftp(self):
        self._ftp.start()
        self._fishbowl_facade.start()
        self._inventory.build(self._ftp, self._fishbowl_facade)
        vendor_configs = self._vendor_config_dao.get_all_items()
        total_inv = build_total_inventory(self._inventory, self._ftp)
        initial_df = get_initial_dataframe(vendor_configs)
        df = populate_dataframe(total_inv, initial_df, self._ftp,
                                vendor_configs)
        self._ftp.write_df_as_csv(MASTER_INVENTORY_PATH, df)
        self._ftp.close()
        self._fishbowl_facade.close()

    @Manager.action
    @Manager.asynchronous()
    @log_exceptions
    def pricing_ftp(self):
        self._ftp.start()
        coast_vendor_config = self._vendor_config_dao.get_item("Coast To "
                                                               "Coast")
        cost_adjustment_config = coast_vendor_config.cost_adjustment_config
        prices = []
        map_ = get_sku_map(self._ftp, coast_vendor_config)
        rows = self._ftp.get_file_as_list(COAST_PRICING_PATH)
        for row in rows:
            part_num, base_cost = row
            sku = map_.get(part_num)
            adjusted_cost = get_adjusted_cost(sku,
                                              base_cost,
                                              cost_adjustment_config)
            if sku:
                cost_adjustment = adjusted_cost - base_cost
                pricing = get_list_price(sku, base_cost, cost_adjustment)
                prices.append(pricing)
        self._ftp.write_list_as_csv(MASTER_PRICING_PATH, prices)
        self._ftp.close()

    @Manager.action
    @Manager.asynchronous()
    @log_exceptions
    def dynamo(self):
        self._fishbowl_facade.start()
        self._ftp.start()
        self._inventory.build(self._ftp, self._fishbowl_facade)
        self._fishbowl_facade.close()
        self._ftp.close()
        self._inventory_dao.delete_all_items()
        dynamo_inv = self._inventory.convert_to_entries()
        self._inventory_dao.batch_write_items(dynamo_inv)
