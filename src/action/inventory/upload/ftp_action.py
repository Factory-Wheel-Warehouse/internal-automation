from dataclasses import dataclass

from flask import request

from src.action.action import Action
from src.dao import VendorConfigDAO
from src.domain.inventory.inventory import Inventory
from src.facade.fishbowl import FishbowlFacade
from src.facade.ftp.ftp_facade import FTPFacade
from src.util.constants.inventory import MASTER_INVENTORY_PATH
from src.util.inventory.master_inventory_util import build_total_inventory
from src.util.inventory.master_inventory_util import get_initial_dataframe
from src.util.inventory.master_inventory_util import populate_dataframe


@dataclass
class FtpAction(Action):
    ftp: FTPFacade = None
    fishbowl_facade: FishbowlFacade = None
    inventory: Inventory = Inventory()
    vendor_config_dao: VendorConfigDAO = VendorConfigDAO()

    def __post_init__(self):
        if not self.ftp:
            self.ftp = FTPFacade()
        if not self.fishbowl_facade:
            self.outlook_facade = FishbowlFacade()

    def run(self, request_: request):
        self.ftp.start()
        self.fishbowl_facade.start()
        self.inventory.build(self.ftp, self.fishbowl_facade)
        vendor_configs = self.vendor_config_dao.get_all_items()
        total_inv = build_total_inventory(self.inventory, self.ftp)
        initial_df = get_initial_dataframe(vendor_configs)
        df = populate_dataframe(total_inv, initial_df, self.ftp,
                                vendor_configs)
        self.ftp.write_df_as_csv(MASTER_INVENTORY_PATH, df)
        self.ftp.close()
        self.fishbowl_facade.close()
