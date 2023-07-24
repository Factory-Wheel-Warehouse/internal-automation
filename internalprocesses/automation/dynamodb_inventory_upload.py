import io

import dacite
import pandas
from pandas import DataFrame

from internalprocesses import OutlookClient
from internalprocesses.automation.constants import OUTLOOK_CREDENTIALS
from internalprocesses.inventory.part import Part

SOURCE_FILE_SEARCH_QUERY = "?" + "&".join([
    "$search=" + "\"" + " AND ".join([
        "from:ibsam@factorywheelwarehouse.com",
        "subject:Source Inventory",
        "hasAttachment:true"
    ]) + "\"",
    "$top=1",
])


def get_most_recent_source_file() -> DataFrame:
    outlook = OutlookClient(**OUTLOOK_CREDENTIALS)
    message_response = outlook.searchMessages(SOURCE_FILE_SEARCH_QUERY)
    email_id = message_response["id"]
    attachment_response = outlook.getEmailAttachments(email_id)
    attachment_id = attachment_response[0]["id"]
    attachment_bytes = outlook.getEmailAttachmentContent(email_id,
                                                         attachment_id)
    return pandas.read_csv(io.BytesIO(attachment_bytes))


def parse_inventory(inventory_dataframe: DataFrame) -> list[Part]:
    handling_times = []
    for _, row in inventory_dataframe.iterrows():
        handling_times.append(dacite.from_dict(
            data_class=Part,
            data={
                "part_number": row["sku"],
                "handling_times": {
                    "ebay": int(float(row["HT"])),
                    "amazon": int(float(row["final_Walmart_HT"])),
                    "walmart": int(float(row["Amazon_HT"]))
                }
            }
        ))
    return list(handling_times)


def get_most_recent_part_data():
    most_recent_source_file = get_most_recent_source_file()
    return parse_inventory(most_recent_source_file)
