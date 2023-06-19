import time
import traceback
from datetime import date, timedelta

from internalprocesses import aws, OutlookClient
from internalprocesses.automation.automation import InternalAutomation
from internalprocesses.automation.constants import OUTLOOK_CREDENTIALS
from internalprocesses.automation.dynamodb_inventory_upload import \
    get_most_recent_part_data
from internalprocesses.aws.dynamodb import InventoryDAO, ProcessedOrderDAO


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


@log_exceptions
def order_import(test=True):
    automation = InternalAutomation()
    print("Retrieving orders")
    automation.getOrders()
    print(f"Retrieved orders:\n{automation.ordersByVendor}")
    if not test:
        automation.importOrders()
        email = "sales@factorywheelwarehouse.com"
    else:
        email = "danny@factorywheelwarehouse.com"
    for vendor in automation.ordersByVendor:
        automation.emailDropships(automation.ordersByVendor[vendor],
                                  vendor, email)
    automation.emailExceptionOrders(email)
    print("done")


@log_exceptions
def tracking_upload():
    InternalAutomation().addTracking()


@log_exceptions
def warehouse_inventory_upload():
    automation = InternalAutomation()
    inventory = automation.fishbowl.getPartsOnHand()
    formatted_inventory = [[el.strip('"') for el in row.split(",")]
                           for row in inventory]
    automation.ftpServer.write_list_as_csv(r'/Fishbowl/inventory.csv',
                                           formatted_inventory)


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
    ship_by_today = order_dao.get_orders_by_sbd(str(date.today()))
    tomorrow = date.today() + timedelta(days=1)
    ship_by_tomorrow = order_dao.get_orders_by_sbd(str(tomorrow))
    if ship_by_today or ship_by_tomorrow:
        message = ""
        if ship_by_today:
            message += "Orders to ship by today: \n\n"
            message += "\n\n\n".join([str(order) for order in ship_by_today])
        if ship_by_tomorrow:
            message += "\n\n\n\n\n" if message else ""
            message += "Orders to ship by tomorrow: \n\n"
            message += "\n\n\n".join([str(order) for order in
                                      ship_by_tomorrow])
        outlook.sendMail("sales@factorywheelwarehouse.com",
                         "\"Ship By\" Automated Notifications",
                         message)
