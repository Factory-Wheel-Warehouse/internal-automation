import logging
from base64 import b64encode
from io import BytesIO

from src.facade.fishbowl import FishbowlFacade
from src.facade.fishbowl import quantity_sold_by_sku_report
from src.facade.outlook import OutlookFacade


class ReportingService:
    """Handles generation and delivery of reporting artifacts."""

    def __init__(
            self,
            outlook: OutlookFacade | None = None,
            fishbowl: FishbowlFacade | None = None,
            logger: logging.Logger | None = None,
    ):
        self.outlook = outlook or OutlookFacade()
        self.fishbowl = fishbowl or FishbowlFacade()
        self.logger = logger or logging.getLogger(__name__)

    def send_quantity_sold_report(self, recipient: str = "sales@factorywheelwarehouse.com"):
        self.logger.info("Generating quantity sold report for %s", recipient)
        self.outlook.login()
        self.fishbowl.start()
        try:
            rows = [["SKU", "Quantity Sold"]] + quantity_sold_by_sku_report(self.fishbowl)
        finally:
            self.fishbowl.close()

        csv_string = "\n".join(f"{row[0]},{row[1]}" for row in rows)
        attachment = b64encode(BytesIO(csv_string.encode()).read()).decode()
        subject = "Quantity Sold by SKU Sales Data"
        body = (
            "Attached is a CSV file containing SKU's sold in the past year "
            "and how many sold. The csv file is in descending order by quantity sold."
        )
        self.outlook.sendMail(
            recipient,
            subject,
            body,
            attachment=attachment,
            attachmentName="QuantitySoldBySkuReport.csv",
        )
        self.logger.info("Quantity sold report emailed to %s", recipient)
