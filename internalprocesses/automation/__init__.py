import time
import traceback
from base64 import b64encode
from datetime import date, timedelta
from io import BytesIO

from internalprocesses import aws, OutlookClient, FishbowlClient
from internalprocesses.automation.automation import InternalAutomation
from internalprocesses.automation.constants import OUTLOOK_CREDENTIALS, \
    FTP_CREDENTIALS, FISHBOWL_CREDENTIALS
from internalprocesses.automation.dynamodb_inventory_upload import \
    get_most_recent_part_data
from internalprocesses.automation.upload_master_inventory import \
    build_total_inventory, populate_dataframe, get_initial_dataframe, \
    FTP_SAVE_PATH
from internalprocesses.aws.dynamodb import InventoryDAO, ProcessedOrderDAO, \
    VendorConfigDAO
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.inventory import Inventory
from internalprocesses.magentoapi.magento import Environment
from internalprocesses.vendor import VendorConfig


def log_exceptions(func):
    def run(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except BaseException:
            traceback.print_exc()
            exception = traceback.format_exc()
            message = f"Exception encountered during {__name__}" \
                      f"::{func.__name__}\n\n\n{exception}"
            aws.post_exception_to_sns(message)

    return run


# @log_exceptions
def order_import(test=True):
    for env in [Environment.PROD, Environment.STAGING]:
        print(f"Retrieving orders for {env}")
        automation = InternalAutomation(env)
        automation.getOrders()
        print(f"Retrieved orders:\n{automation.ordersByVendor}")
        if not test:
            automation.importOrders()
            email = "orders@factorywheelwarehouse.com"
        else:
            email = "danny@factorywheelwarehouse.com"
        for vendor in automation.ordersByVendor:
            automation.emailDropships(automation.ordersByVendor[vendor],
                                      vendor, email)
        automation.emailExceptionOrders(email)
        automation.close()
        print("done")


@log_exceptions
def tracking_upload():
    for env in [Environment.PROD, Environment.STAGING]:
        print(f"Uploading tracking for {env}")
        automation = InternalAutomation(env)
        automation.addTracking()
        automation.close()


@log_exceptions
def warehouse_inventory_upload():
    automation = InternalAutomation()
    inventory = automation.fishbowl.getPartsOnHand()
    formatted_inventory = [[el.strip('"') for el in row.split(",")]
                           for row in inventory]
    automation.ftpServer.write_list_as_csv(r'/Fishbowl/inventory.csv',
                                           formatted_inventory)
    automation.close()


@log_exceptions
def update_inventory_source_data():
    start = time.time()
    inventory_dao = InventoryDAO()
    print("Retrieving inventory data...", "")
    data = get_most_recent_part_data()
    print("Deleting and recreating database...", "")
    inventory_dao.delete_all_items()
    print("Writing data to database", "")
    inventory_dao.batch_write_items(data, len(data))
    print(f"Rebuilt inventory database in {time.time() - start} seconds")


@log_exceptions
def email_ship_by_notifications():
    outlook = OutlookClient(**OUTLOOK_CREDENTIALS)
    order_dao = ProcessedOrderDAO()
    ship_by_today = filter(lambda order: not order.shipped,
                           order_dao.get_orders_by_sbd(str(date.today())))
    tomorrow = date.today() + timedelta(days=1)
    ship_by_tomorrow = filter(lambda order: not order.shipped,
                              order_dao.get_orders_by_sbd(str(tomorrow)))
    if ship_by_today or ship_by_tomorrow:
        message = ""
        if ship_by_today:
            message += "Orders to ship by today: \n\n"
            message += "\n\n\n".join([str(order) for order in
                                      ship_by_today])
        if ship_by_tomorrow:
            message += "\n\n\n\n\n" if message else ""
            message += "Orders to ship by tomorrow: \n\n"
            message += "\n\n\n".join([str(order) for order in
                                      ship_by_tomorrow])
        outlook.sendMail("sales@factorywheelwarehouse.com",
                         "\"Ship By\" Automated Notifications",
                         message)


@log_exceptions
def upload_master_inventory():
    vendor_configs: list[VendorConfig] = VendorConfigDAO().get_all_items()
    ftp = FTPConnection(**FTP_CREDENTIALS)
    fishbowl = FishbowlClient(**FISHBOWL_CREDENTIALS)
    inventory = Inventory(vendor_configs, ftp, fishbowl)
    total_inv = build_total_inventory(inventory, ftp)
    df = populate_dataframe(total_inv, get_initial_dataframe(
        vendor_configs), ftp, {v.vendor_name: v for v in vendor_configs})
    ftp.write_df_as_csv(FTP_SAVE_PATH, df)
    outlook = OutlookClient(**OUTLOOK_CREDENTIALS)
    file = BytesIO()
    df.to_csv(file, index=False)
    file.seek(0)
    date_ = date.today().isoformat()
    outlook.sendMail(to="sales@factorywheelwarehouse.com",
                     subject="Master Inventory Sheet",
                     body="File attached",
                     attachment=b64encode(file.read()).decode(),
                     attachmentName=f"fww_master_inventory_"
                                    f"{date_}.csv")
    del inventory
