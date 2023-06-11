import traceback

from internalprocesses import aws
from internalprocesses.automation.automation import InternalAutomation
from internalprocesses.automation.dynamodb_inventory_upload import \
    update_inventory_source_data


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


# @log_exceptions
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
def upload_inventory_to_dynamodb():
    update_inventory_source_data()
