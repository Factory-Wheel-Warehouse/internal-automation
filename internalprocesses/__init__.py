# import all and define necessary functions
# from internalprocesses.masterinventory.mergeinventory import emailInventorySheet
from base64 import b64encode
from io import BytesIO
import os
import json
from traceback import print_exc
from dotenv import load_dotenv
from .outlookapi import OutlookClient
from .fishbowlclient import FBConnection, quantitySoldBySKUReport


def emailQuantitySoldReport():
    try:
        load_dotenv()
        fbPassword = os.getenv("FISHBOWL-PW")
        outlookPassword = os.getenv("OUTLOOK-PW")
        outlookCS = os.getenv("OUTLOOK-CS")
        with open(
                os.path.join(
                    os.path.dirname(__file__), "..", "data/config.json"
                )
        ) as configFile:
            outlookConfig = json.load(configFile)["APIConfig"]["Outlook"][
                "Danny"]
        outlook = OutlookClient(outlookConfig, outlookPassword, outlookCS)
        fishbowl = FBConnection("danny", fbPassword,
                                "factorywheelwarehouse.myfishbowl.com")
        reportAsList = [["SKU", "Quantity Sold"]] + quantitySoldBySKUReport(
            fishbowl)
        reportAsCsvString = "\n".join(
            [f"{row[0]},{row[1]}" for row in reportAsList])
        reportBinary = BytesIO(reportAsCsvString.encode()).read()
        reportEDMBinary = b64encode(reportBinary).decode()
        subject = "Quantity Sold by SKU Sales Data"
        body = "Attached is a CSV file containing SKU's sold in the past year and how many sold. The csv file is in descending order by quantity sold."
        outlook.sendMail(
            "sales@factorywheelwarehouse.com", subject, body,
            attachment=reportEDMBinary,
            attachmentName="QuantitySoldBySkuReport.csv"
        )
    except:
        print_exc()
    finally:
        fishbowl.close()
