from threading import Thread

from dataclasses import dataclass

from flask import Flask

from src.dao.vendor_config_dao import VendorConfigDAO
from src.domain.inventory import Inventory
from src.facade.fishbowl import FishbowlFacade
from src.facade.ftp.ftp_facade import FTPFacade
from src.facade.outlook import OutlookFacade
from src.manager.inventory import InventoryManager
from src.manager.manager import Manager

app = Flask(__name__)
app.add_url_rule("/", view_func=lambda: "Index")
app.add_url_rule("/index", "home", lambda: "Home")
app.add_url_rule("/index", "random", lambda: "Random")


# from internalprocesses import email_quantity_sold_report
# from src.facade.fishbowl import FishbowlFacade
# from src.manager.inventory.inventory_upload_manager import \
#     InventoryUploadManager
# from src.util.constants.credentials import FISHBOWL_CREDENTIALS


@dataclass
class FlaskService:
    manager: Manager


@dataclass
class FlaskServer:
    app: Flask
    services: list[FlaskService]

    def __post_init__(self):
        for service in services:
            self._add_routes(service)

    def _add_routes(self, service: FlaskService):
        self.app.add_url_rule(service.manager.endpoint,
                              view_func=service.manager.list)
        for name in service.manager.get_actions():
            route = f"{service.manager.endpoint}/{name}"
            func = getattr(service.manager, name)
            self.app.add_url_rule(route, view_func=func)


app = Flask(__name__)

services = [
    FlaskService(InventoryManager()),
]
server = FlaskServer(app, services)
#
# fishbowl_facade = FishbowlFacade(**FISHBOWL_CREDENTIALS)
#
# inventory_upload_manager = InventoryUploadManager(fishbowl_facade)
#
# app.add_url_rule()
#
#
# @app.route("/")
# def index():
#     return "<h1>Service is live<h1>"
#
#
# @app.route("/import-orders")
# def orderImport():
#     orderImportThread = Thread(target=orderImportNewThread, args=(False,))
#     orderImportThread.start()
#     return "Success"
#
#
# @app.route("/import-orders-test")
# def orderImportTest():
#     orderImportThread = Thread(target=order_import)
#     orderImportThread.start()
#     return "Success"
#
#
# @app.route("/upload-tracking")
# def trackingUpload():
#     trackingUploadThread = Thread(target=trackingUploadNewThread)
#     trackingUploadThread.start()
#     return "Success"
#
#
# @app.route("/inventory-upload")
# def inventoryUpload():
#     inventoryUploadThread = Thread(target=inventoryUploadNewThread)
#     inventoryUploadThread.start()
#     return "Success"
#
#
# @app.route("/email-inventory-file")
# def emailInventoryFile():
#     emailInventoryFileThread = Thread(target=emailInventorySheetNewThread)
#     emailInventoryFileThread.start()
#     return "Success"
#
#
# @app.route("/yearly-sold-report")
# def emailSoldReport():
#     emailSoldReportThread = Thread(target=email_quantity_sold_report)
#     emailSoldReportThread.start()
#     return "Success"
#
#
# @app.route("/upload_inventory_source_data")
# def upload_inventory_source_data():
#     inventory_upload_manager.start()
#     return "Success"
#
#
# @app.route("/warehouse-inventory-upload")
# def warehouse_inventory_upload_endpoint():
#     Thread(target=warehouse_inventory_upload).start()
#     return "Success"
#
#
# @app.route("/email_ship_by_notifications")
# def email_sbd():
#     Thread(target=email_ship_by_notifications).start()
#     return "Success"
#
#
# def trackingUploadNewThread():
#     tracking_upload()
#
#
# def orderImportNewThread(test=True):
#     order_import(test=test)
#
#
# def inventoryUploadNewThread():
#     InventoryUploadManager()
#
#
# def emailInventorySheetNewThread():
#     emailInventorySheet()
#

if __name__ == "__main__":
    app.run(debug=True)
