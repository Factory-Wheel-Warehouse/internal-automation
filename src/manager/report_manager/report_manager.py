from base64 import b64encode
from io import BytesIO

from src.facade.fishbowl import FishbowlFacade
from src.facade.fishbowl import quantity_sold_by_sku_report
from src.facade.outlook import OutlookFacade
from src.manager.manager import Manager


class ReportManager(Manager):

    @property
    def endpoint(self):
        return "report"

    @Manager.action
    @Manager.asynchronous()
    def quantity_sold(self):
        outlook = OutlookFacade()
        fishbowl = FishbowlFacade()
        outlook.login()
        fishbowl.start()
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
        fishbowl.close()
