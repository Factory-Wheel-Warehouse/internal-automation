import logging
from base64 import b64encode
from datetime import date

from src.dao import InventoryDAO, VendorConfigDAO
from src.domain.inventory.inventory import Inventory
from src.facade.fishbowl import FishbowlFacade
from src.facade.ftp.ftp_facade import FTPFacade
from src.facade.outlook import OutlookFacade
from src.util.constants.inventory import MASTER_INVENTORY_PATH
from src.util.inventory.master_inventory_util import (
    build_total_inventory,
    get_initial_dataframe,
    populate_dataframe,
)


class InventorySyncService:
    """Coordinates inventory publishing, Dynamo syncs, and email delivery."""

    def __init__(
            self,
            ftp: FTPFacade | None = None,
            fishbowl: FishbowlFacade | None = None,
            outlook: OutlookFacade | None = None,
            inventory: Inventory | None = None,
            vendor_config_dao: VendorConfigDAO | None = None,
            inventory_dao: InventoryDAO | None = None,
            master_inventory_path: str = MASTER_INVENTORY_PATH,
            logger: logging.Logger | None = None,
    ):
        self.ftp = ftp or FTPFacade()
        self.fishbowl = fishbowl or FishbowlFacade()
        self.outlook = outlook or OutlookFacade()
        self.inventory = inventory or Inventory()
        self.vendor_config_dao = vendor_config_dao or VendorConfigDAO()
        self.inventory_dao = inventory_dao or InventoryDAO()
        self.master_inventory_path = master_inventory_path
        self.logger = logger or logging.getLogger(__name__)

    # Public operations -------------------------------------------------

    def publish_master_inventory(self):
        self._start_inventory_sources()
        try:
            df = self._build_master_inventory_dataframe()
            self.ftp.write_df_as_csv(self.master_inventory_path, df)
            self.logger.info("Master inventory written to FTP")
        finally:
            self._stop_inventory_sources()

    def sync_dynamo(self):
        self._start_inventory_sources()
        try:
            self.inventory.build(self.ftp, self.fishbowl)
        finally:
            self._stop_inventory_sources()
        self.inventory_dao.delete_all_items()
        self.inventory_dao.batch_write_items(self.inventory.convert_to_entries())
        self.logger.info("Dynamo inventory synced")

    def email_master_inventory(self):
        self.ftp.start()
        try:
            self.outlook.login()
            file = self.ftp.get_file_as_binary(self.master_inventory_path)
            encoded_file = b64encode(file.read()).decode()
            file_name = f"fww_master_inventory_{date.today().isoformat()}.csv"
            self.outlook.sendMail(
                to="sales@factorywheelwarehouse.com",
                subject="Master Inventory Sheet",
                body="File attached",
                attachment=encoded_file,
                attachmentName=file_name,
            )
            self.logger.info("Master inventory emailed")
        finally:
            self.ftp.close()

    # Internal helpers --------------------------------------------------

    def _build_master_inventory_dataframe(self):
        self.inventory.build(self.ftp, self.fishbowl)
        vendor_configs = self.vendor_config_dao.get_all_items()
        total_inventory = build_total_inventory(self.inventory, self.ftp)
        initial_df = get_initial_dataframe(vendor_configs)
        return populate_dataframe(total_inventory, initial_df, self.ftp, vendor_configs)

    def _start_inventory_sources(self):
        self.ftp.start()
        self.fishbowl.start()

    def _stop_inventory_sources(self):
        self.fishbowl.close()
        self.ftp.close()
