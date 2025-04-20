from base64 import b64encode
from dataclasses import dataclass
from datetime import date

from flask import request

from src.action.action import Action
from src.facade.ftp.ftp_facade import FTPFacade
from src.facade.outlook import OutlookFacade
from src.util.constants.inventory import MASTER_INVENTORY_PATH


@dataclass
class EmailInventoryAction(Action):
    ftp: FTPFacade = None
    outlook_facade: OutlookFacade = None

    def __post_init__(self):
        if not self.ftp:
            self.ftp = FTPFacade()
        if not self.outlook_facade:
            self.outlook_facade = OutlookFacade()

    def run(self, request_: request):
        self.ftp.start()
        self.outlook_facade.login()
        file = self.ftp.get_file_as_binary(MASTER_INVENTORY_PATH)
        encoded_file = b64encode(file.read()).decode()
        date_ = date.today().isoformat()
        file_name = f"fww_master_inventory_{date_}.csv"
        self.outlook_facade.sendMail(
            to="sales@factorywheelwarehouse.com",
            subject="Master Inventory Sheet",
            body="File attached",
            attachment=encoded_file,
            attachmentName=file_name)
        self.ftp.close()
