import io

import dacite
import pandas
from pandas import DataFrame

from internalprocesses import OutlookFacade
from src.domain.inventory.part import Part
from src.util.constants.credentials import OUTLOOK_CREDENTIALS

SOURCE_FILE_SEARCH_QUERY = "?" + "&".join([
    "$search=" + "\"" + " AND ".join([
        "from:ibsam@factorywheelwarehouse.com",
        "subject:Source Inventory",
        "hasAttachment:true"
    ]) + "\"",
    "$top=1",
])


def get_most_recent_source_file() -> DataFrame:
    outlook = OutlookFacade(**OUTLOOK_CREDENTIALS)
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
def upload_master_inventory():
    vendor_configs: list[VendorConfig] = VendorConfigDAO().get_all_items()
    ftp = FTPFacade(**FTP_CREDENTIALS)
    fishbowl = FishbowlFacade(**FISHBOWL_CREDENTIALS)
    inventory = Inventory(vendor_configs, ftp, fishbowl)
    total_inv = build_total_inventory(inventory, ftp)
    df = populate_dataframe(total_inv, get_initial_dataframe(
        vendor_configs), ftp, {v.vendor_name: v for v in vendor_configs})
    ftp.write_df_as_csv(MASTER_INVENTORY_PATH, df)
    outlook = OutlookFacade(**OUTLOOK_CREDENTIALS)
    file = BytesIO()
    df.to_csv(file, index=False)
    file.seek(0)
    date_ = date.today().isoformat()
    outlook.sendMail(to="danny@factorywheelwarehouse.com",
                     subject="Master Inventory Sheet",
                     body="File attached",
                     attachment=b64encode(file.read()).decode(),
                     attachmentName=f"fww_master_inventory_"
                                    f"{date_}.csv")
