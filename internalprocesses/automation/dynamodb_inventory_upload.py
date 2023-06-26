import io
import pprint
import time

import dacite
from pandas import read_csv

from internalprocesses import OutlookClient
from internalprocesses.automation import InternalAutomation
from internalprocesses.automation.constants import OUTLOOK_CREDENTIALS
from internalprocesses.aws.dynamodb import ProcessedOrderDAO
from internalprocesses.inventory.part import Part

SOURCE_FILE_SEARCH_QUERY = "?" + "&".join([
    "$search=" + "\"" + " AND ".join([
        "from:ibsam@factorywheelwarehouse.com",
        "subject:Source Inventory",
        "hasAttachment:true"
    ]) + "\"",
    "$top=1",
])


def get_most_recent_source_file() -> list:
    outlook = OutlookClient(**OUTLOOK_CREDENTIALS)
    message_response = outlook.searchMessages(SOURCE_FILE_SEARCH_QUERY)
    email_id = message_response["id"]
    attachment_response = outlook.getEmailAttachments(email_id)
    attachment_id = attachment_response[0]["id"]
    attachment_bytes = outlook.getEmailAttachmentContent(email_id,
                                                         attachment_id)
    return list(
        read_csv(filepath_or_buffer=io.BytesIO(attachment_bytes)).values)


def parse_inventory(inventory_list: list[any]) -> list[Part]:
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


def get_most_recent_part_data():
    most_recent_source_file = get_most_recent_source_file()
    return parse_inventory(most_recent_source_file)
