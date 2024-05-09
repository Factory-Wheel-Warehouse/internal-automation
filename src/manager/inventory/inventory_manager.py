from base64 import b64encode
from datetime import date

from src.facade.outlook import OutlookFacade
from src.manager.inventory.inventory_upload_manager import \
    InventoryUploadManager
from src.manager.manager import Manager
from src.facade.ftp.ftp_facade import FTPFacade
from src.util.constants.inventory import MASTER_INVENTORY_PATH


class InventoryManager(Manager):
    _ftp: FTPFacade = FTPFacade()
    _outlook_facade: OutlookFacade = OutlookFacade()

    @property
    def endpoint(self):
        return "inventory"

    @Manager.sub_manager
    def upload(self):
        return InventoryUploadManager()

    @Manager.action
    @Manager.asynchronous()
    def email_inventory_file(self):
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
