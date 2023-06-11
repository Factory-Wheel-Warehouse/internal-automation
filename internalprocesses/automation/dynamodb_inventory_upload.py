import io
import time

import dacite
from pandas import read_csv

from internalprocesses import OutlookClient
from internalprocesses.automation.constants import OUTLOOK_CREDENTIALS
from internalprocesses.aws.dynamodb import InventoryDAO, VendorConfigDAO
from internalprocesses.inventory.part import Part

_SOURCE_FILE_SEARCH_QUERY = "?" + "&".join([
    "$search=" + "\"" + " AND ".join([
        "from:ibsam@factorywheelwarehouse.com",
        "subject:Source Inventory",
        "hasAttachment:true"
    ]) + "\"",
    "$top=1",
])


def _get_most_recent_source_file() -> list:
    outlook = OutlookClient(**OUTLOOK_CREDENTIALS)
    message_response = outlook.searchMessages(_SOURCE_FILE_SEARCH_QUERY)
    email_id = message_response["id"]
    attachment_response = outlook.getEmailAttachments(email_id)
    attachment_id = attachment_response[0]["id"]
    attachment_bytes = outlook.getEmailAttachmentContent(email_id,
                                                         attachment_id)
    return list(
        read_csv(filepath_or_buffer=io.BytesIO(attachment_bytes)).values)


def _parse_inventory(inventory_list: list[any]) -> list[Part]:
    handling_times = []
    for row in inventory_list:
        handling_times.append(dacite.from_dict(
            data_class=Part,
            data={
                "part_number": row[0],
                "handling_times": {
                    "ebay": int(float(str(row[40]))),
                    "amazon": int(float(str(row[41]))),
                    "walmart": int(float(str(row[42])))
                }
            }
        ))
    return list(handling_times)


def _get_most_recent_part_data():
    most_recent_source_file = _get_most_recent_source_file()
    return _parse_inventory(most_recent_source_file)


def update_inventory_source_data():
    start = time.time()
    inventory_dao = InventoryDAO()
    print("Retrieving inventory data...", "")
    data = _get_most_recent_part_data()
    print("Deleting and recreating database...", "")
    inventory_dao.delete_all_items()
    print("Writing data to database", "")
    inventory_dao.batch_write_items(data, len(data))
    print(f"Rebuilt inventory database in {time.time() - start} seconds")


if __name__ == "__main__":
    update_inventory_source_data()
