from base64 import b64encode
from io import BytesIO
import os
import json
from traceback import print_exc
from dotenv import load_dotenv
from .outlookapi import OutlookClient
from .fishbowl import FishbowlClient, quantity_sold_by_sku_report


def email_quantity_sold_report():
    try:
        load_dotenv()
        fb_password = os.getenv("FISHBOWL-PW")
        outlook_password = os.getenv("OUTLOOK-PW")
        outlook_cs = os.getenv("OUTLOOK-CS")
        with open(
                os.path.join(
                    os.path.dirname(__file__), "..", "data/config.json"
                )
        ) as configFile:
            outlook_config = json.load(configFile)["APIConfig"]["Outlook"][
                "Danny"]
        outlook = OutlookClient(outlook_config, outlook_password, outlook_cs)
        fishbowl = FishbowlClient("danny", fb_password,
                                  "factorywheelwarehouse.myfishbowl.com")
        report_as_list = [["SKU",
                           "Quantity Sold"]] + quantity_sold_by_sku_report(
            fishbowl)
        report_as_csv_string = "\n".join(
            [f"{row[0]},{row[1]}" for row in report_as_list])
        report_binary = BytesIO(report_as_csv_string.encode()).read()
        report_edm_binary = b64encode(report_binary).decode()
        subject = "Quantity Sold by SKU Sales Data"
        body = "Attached is a CSV file containing SKU's sold in the past " \
               "year and how many sold. The csv file is in descending order " \
               "by quantity sold."
        outlook.sendMail(
            "sales@factorywheelwarehouse.com", subject, body,
            attachment=report_edm_binary,
            attachmentName="QuantitySoldBySkuReport.csv"
        )
    except:
        print_exc()
    finally:
        fishbowl.close()
