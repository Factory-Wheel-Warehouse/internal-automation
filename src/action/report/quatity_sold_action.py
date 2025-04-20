from base64 import b64encode
from dataclasses import dataclass
from io import BytesIO

from flask import request

from src.action.action import Action
from src.facade.fishbowl import FishbowlFacade
from src.facade.fishbowl import quantity_sold_by_sku_report
from src.facade.outlook import OutlookFacade


@dataclass
class QuantitySoldAction(Action):
    outlook: OutlookFacade = OutlookFacade()
    fishbowl: FishbowlFacade = FishbowlFacade()

    def run(self, request_: request):
        self.outlook.login()
        self.fishbowl.start()
        report_as_list = [["SKU",
                           "Quantity Sold"]] + quantity_sold_by_sku_report(
            self.fishbowl)
        self.fishbowl.close()
        report_as_csv_string = "\n".join(
            [f"{row[0]},{row[1]}" for row in report_as_list])
        report_binary = BytesIO(report_as_csv_string.encode()).read()
        report_edm_binary = b64encode(report_binary).decode()
        subject = "Quantity Sold by SKU Sales Data"
        body = "Attached is a CSV file containing SKU's sold in the past " \
               "year and how many sold. The csv file is in descending order " \
               "by quantity sold."
        self.outlook.sendMail(
            "sales@factorywheelwarehouse.com", subject, body,
            attachment=report_edm_binary,
            attachmentName="QuantitySoldBySkuReport.csv"
        )
