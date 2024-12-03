import os
import pprint
import re
import json
from datetime import date
from datetime import datetime
from datetime import timedelta

from dotenv import load_dotenv

from src.dao.processed_order_dao import ProcessedOrderDAO
from src.dao.vendor_config_dao import VendorConfigDAO
from src.domain.fishbowl.sales_order_item_type import SalesOrderItemType
from src.domain.inventory.inventory import Inventory
from src.domain.order.address import Address
from src.domain.order.order import Order
from src.facade.fishbowl import FishbowlFacade
from src.facade.ftp.ftp_facade import FTPFacade
from src.facade.magento.magento_facade import Environment
from src.facade.magento.magento_facade import MagentoFacade
from src.facade.outlook import OutlookFacade
from src.util.constants.inventory import PAINT_CODE_START
from src.util.constants.order import CHANNEL_FEE
from src.util.constants.order import WALMART_FEE
from src.util.logging.cloudwatch_logger import LOGGER
from src.util.order.magento_parsing_utils import get_channel_fee
from src.util.tracking.tracking_checker import TrackingChecker
from src.util.tracking.util import get_tracking_from_outlook


class InternalAutomationFacade:

    def __init__(self, env: Environment = Environment.PROD):
        load_dotenv()
        self.config = self.readConfig()
        self.ordersByVendor = {}
        self.vendors = {v.vendor_name: v for v in
                        VendorConfigDAO().get_all_items()}
        self.exceptionOrders = []
        self.customers = self.config["Main Settings"]["Customers"]
        self.ftpServer = FTPFacade()
        self.fishbowl = FishbowlFacade()
        self.outlook = OutlookFacade()
        self.magento = MagentoFacade()
        self.sourceList = Inventory()
        self.trackingChecker = TrackingChecker()
        self.unfulfilledOrders = self.magento.get_pending_orders()

        self.fishbowl.start()
        self.ftpServer.start()

        self.outlook.login()
        self.sourceList.build(self.ftpServer, self.fishbowl)

    def close(self):

        """Closes all necessary connections."""

        self.fishbowl.close()
        self.ftpServer.close()

    def readConfig(self) -> dict:

        """Returns the loaded config.json file."""

        cd = os.path.dirname(__file__)
        configFile = os.path.join(cd, "..", "..", "..", "data/config.json")
        return json.load(open(configFile))

    def getTracking(self, customer_po: str) -> str | None:

        """Checks for a tracking number for the customer_po passed in"""
        if customer_po[0].isalpha():
            customer_po = customer_po[1:]
        if not self.fishbowl.isSO(customer_po):
            return
        po_num = self.fishbowl.getPONum(customer_po)
        if po_num:
            tracking_numbers = get_tracking_from_outlook(po_num, self.outlook)
            if len(tracking_numbers) == 1:
                return list(tracking_numbers.values())[0][0]
        else:
            tracking_numbers = self.fishbowl.getTracking(customer_po)
            if tracking_numbers:
                return tracking_numbers[0]

    def checkTrackingStatus(self,
                            trackingNumber: str,
                            carrier: str,
                            customer_po: str
                            ) -> tuple[str, datetime]:

        """
        Checks the tracking status of a tracking number
        """

        trackingData = self.trackingChecker.get_tracking_details(
            trackingNumber, carrier
        )
        if self.trackingChecker.status_code == 200:
            status = trackingData["data"][0]["status"]
            origin_info = trackingData["data"][0].get("origin_info")
            if origin_info and origin_info.get("ItemReceived"):
                received_date = datetime.strptime(
                    trackingData["data"][0]["origin_info"]["ItemReceived"],
                    "%Y-%m-%d %H:%M:%S"
                )
            else:
                received_date = datetime.now()
            return status, received_date
        else:
            self.trackingChecker.add_single_tracking(
                trackingNumber, carrier, customer_po
            )
            return self.checkTrackingStatus(
                trackingNumber, carrier, customer_po
            )

    def add_tracking_number_and_fulfill(self, customer_po, tracking_number,
                                        po, zero_cost_pos) -> None:
        self.magento.addOrderTracking(customer_po,
                                      tracking_number)
        if customer_po[0].isalpha():
            reference_customer_po = customer_po[1:]
        else:
            reference_customer_po = customer_po
        if ProcessedOrderDAO().get_item(reference_customer_po):
            ProcessedOrderDAO().mark_order_shipped(reference_customer_po)
        # if po:
        #     try:
        #         if not self.fishbowl.fulfill_po(po):
        #             zero_cost_pos.append(po)
        #     except:
        #         print(f"{po} already fulfilled")

    def addTracking(self) -> None:

        """
        Adds tracking numbers to unshipped orders with available tracking
        """

        tracking = {}
        for customer_po in self.unfulfilledOrders:
            tracking_num = self.getTracking(customer_po)
            if tracking_num:
                tracking[customer_po] = tracking_num
        LOGGER.info(f"Found tracking numbers for {len(tracking)} orders"
                    f"\nTracking: {tracking}")
        zero_cost_pos = []
        uploaded = 0
        for customer_po, trackingNumber in tracking.items():
            if customer_po[0].isalpha():
                po = self.fishbowl.getPONum(customer_po[0])
            else:
                po = self.fishbowl.getPONum(customer_po)
            carrier = self.magento.getCarrier(trackingNumber)
            status, received_date = self.checkTrackingStatus(
                trackingNumber, carrier, customer_po
            )
            status_is_valid = status in ["transit", "pickup", "delivered"]
            lookback_window = datetime.today() - timedelta(days=10)
            received_date_is_valid = received_date >= lookback_window
            if status_is_valid and received_date_is_valid:
                self.add_tracking_number_and_fulfill(customer_po,
                                                     trackingNumber, po,
                                                     zero_cost_pos)
        if zero_cost_pos:
            self.outlook.sendMail("sales@factorywheelwarehouse.com",
                                  "Unfulfilled POs with Tracking Received",
                                  "The following POs have had tracking "
                                  "uploaded but had zero cost PO items:\n\n"
                                  f"{zero_cost_pos}")

        LOGGER.info(f"Tracking completed successfully with {uploaded}"
                    f" tracking uploaded")

    def buildSOItemString(self, order: Order, vendor: str) -> str:

        """
        Takes in an Order object and builds the row to be used in the Fishbowl 
        import for the item ordered.

        Keyword Argument:

            order: Order
                customer order being processed

        Return:

            str : formatted row describing the item
        """

        itemType = SalesOrderItemType.SALE
        if vendor != "Warehouse":
            itemType = SalesOrderItemType.DROP_SHIP
        string = f'"Item", {itemType}, "{order.hollander}", , {order.qty}, '
        string += f'"ea", {order.price}, , , , , , , , , '
        return string

    @staticmethod
    def get_channel_fee_so_line(channel_fee: float) -> str:
        return f'"Item", {SalesOrderItemType.DISCOUNT_AMOUNT}, ' \
               f'"{CHANNEL_FEE}", , , , {-1 * channel_fee}, , , , , , , , , '

    @staticmethod
    def get_walmart_discount_percent_line() -> str:
        return f'"Item", {SalesOrderItemType.DISCOUNT_PERCENTAGE}, ' \
               f'"{WALMART_FEE}", , , , , , , , , , , , , '

    def buildSOString(self, customer: str, order: Order) -> str:

        """
        Takes in Order object and customer (really selling avenue) and builds 
        the row describing the sales order.

        Keyword Arguments:

            customer : dict
                dictionary describing the customer as defined in config.json
            
            order : Order
                order object being processed
            
        Return:

            str: formatted row describing the sales order
        """

        string = f'"SO", , 20, "{customer["Name"]}", "{customer["Name"]}", '
        string += f'"{customer["Name"]}", "{customer["Address"]}", '
        string += f'"{customer["City"]}", "{customer["State"]}", '
        string += f'"{customer["Zipcode"]}", "{customer["Country"]}", '
        string += rf'"{order.address.name}", "{order.address.street}", '
        string += f'"{order.address.city}", "{order.address.state}", '
        string += f'"{order.address.zipcode}", "United States", "false", '
        string += f'"UPS", "None", 30, "{order.customer_po}"'
        return string

    def buildSOData(self, customer: str, order: Order,
                    vendor: str) -> list[str]:

        """
        Returns the formatted sales order and item data for import given an
        order object and customer details.
        
        Keyword Arguments:

            customer : dict
                dictionary of customer information as defined in config.json
            
            order : Order
                order object to process
        
        Return:

            list : list consisting of the rows as strings [soDetails, item]
        """

        if not order.channel_fee and order.account == "walmart":
            channel_fee = self.get_walmart_discount_percent_line()
        else:
            channel_fee = self.get_channel_fee_so_line(order.channel_fee)

        return [
            self.buildSOString(customer, order),
            self.buildSOItemString(order, vendor),
            channel_fee
        ]

    def buildPOItemString(self, order: Order) -> str:

        """
        Takes in an Order object and builds the row to be used in the Fishbowl 
        import for the item to be purchased.

        Keyword Argument:

            order: Order
                customer order being processed

        Return:

            str : formatted row describing the item
        """

        item_data = ["Item", 10, order.hollander, order.hollander,
                     order.qty, "ea", order.cost]
        return ", ".join([str(element) for element in item_data])

    def buildPOString(self, vendor_name: str, order: Order) -> str:

        """
        Takes in Order object and vendor (really dropshipper) and builds 
        the row describing the purchase order.

        Keyword Arguments:

            vendor_name : dict
                dictionary describing the customer as defined in config.json
            
            order: Order
                order object being processed
            
        Return:

            str: formatted row describing the sales order
        """
        vendor = self.vendors.get(vendor_name)
        if vendor:
            po_data = ["PO", order.poNum, 20, vendor_name, "",
                       vendor.address.vendor_name, vendor.address.street,
                       vendor.address.city, vendor.address.state,
                       vendor.address.zipcode, vendor.address.country,
                       order.address.name, order.address.name,
                       order.address.street, order.address.city,
                       order.address.state, order.address.zipcode,
                       "UNITED STATES", "UPS"]
            return ", ".join([str(element) for element in po_data])
        raise Exception("Vendor name not in vendor list")

    def buildPOData(self, vendor: str, order: Order) -> list[str]:

        """
        Returns the formatted purchase order and item data for import given an
        order object and vendor.
        
        Keyword Arguments:

            vendor : str
                vendor name
            
            order : Order
                order object to process
        
        Return:

            list : list consisting of the rows as strings [soDetails, item]
        """

        return [
            self.buildPOString(vendor, order),
            self.buildPOItemString(order)
        ]

    def getMagentoAddress(self, orderDetails: dict) -> Address:
        shipping = orderDetails["extension_attributes"] \
            ["shipping_assignments"][0]["shipping"]["address"]
        if not shipping["firstname"]:
            shipping["firstname"] = ""
        if not shipping["lastname"]:
            shipping["lastname"] = ""
        address = Address(
            " ".join([shipping["firstname"] or "",
                      shipping["lastname"] or ""]),
            shipping["street"][0],
            shipping["city"], shipping["region_code"],
            shipping["postcode"]
        )
        if len(shipping["street"]) > 1:
            address.street2 = shipping["street"][1]
        return address

    def checkForValidSKU(self, sku: str) -> str | None:
        pattern = r'(ALY|STL)[0-9]{5}[A-Z]{1}[0-9]{2}[N]?'
        search = re.search(pattern, sku.upper())
        if search:
            return search.group()

    def buildMagentoOrder(self,
                          orderDetails: dict,
                          orderID: str,
                          address: Address
                          ) -> Order | None:
        lineItems = orderDetails["items"]
        if lineItems and len(lineItems) == 1:
            item = lineItems[0]
            sku = self.checkForValidSKU(item["sku"])
            if not sku:
                sku = self.checkForValidSKU(item["name"])
            if self.magento.isEbayOrder(orderID):
                account = self.magento.getEbayAccount(orderID)
                orderID = orderID[1:]
            else:
                account = self.magento.get_platform(orderID)
            if sku:
                order = {
                    "address": address,
                    "customer_po": orderID,
                    "hollander": sku,
                    "qty": int(item["qty_ordered"]),
                    "price": float(item["price"]),
                    "platform": self.magento.get_platform(orderID),
                    "account": account,
                    "channel_fee": get_channel_fee(orderDetails)
                }
                return Order(**order)
        if not self.fishbowl.isSO(orderID):
            self.exceptionOrders.append(
                f"Order #{orderID}\n\n"
            )

    def readMagentoOrders(self) -> None:
        for orderID in self.unfulfilledOrders:
            orderDetails = self.magento.get_order_details(orderID)
            address = self.getMagentoAddress(orderDetails)
            order = self.buildMagentoOrder(orderDetails, orderID, address)
            if order and not self.fishbowl.isSO(order.customer_po):
                self.sortOrder(order)

    def getOrders(self) -> None:

        """Organizes orders from each selling avenue into ordersByVendor."""

        self.readMagentoOrders()

    def emailDropships(self, orders, vendor, emailAddress) -> None:

        """
        Drop ships orders from Coast to Coast.

        Keyword Arguments:

            orders : list
                orders to be drop shipped from coast to coast
        """
        emailBody = ""
        for i in range(len(orders)):
            if i > 0:
                emailBody += "\n\n"
            emailBody += str(orders[i])
            if i < len(orders) - 1:
                emailBody += "\n\n"
                emailBody += "-" * 44
        self.outlook.sendMail(emailAddress, f"{vendor} Orders", emailBody)

    def emailExceptionOrders(self, emailAddress: str) -> None:
        if self.exceptionOrders:
            emailBody = ""
            for exceptionOrder in self.exceptionOrders:
                emailBody += exceptionOrder
            self.outlook.sendMail(
                emailAddress,
                "Multiline/Exception Orders", emailBody
            )

    def importOrders(self, test: bool = False):

        """Sends an import request to import all pending sales."""

        for vendor in self.ordersByVendor:
            for order in self.ordersByVendor[vendor]:
                if not self.fishbowl.isProduct(order.hollander):
                    self.fishbowl.importProduct(order.hollander)
                customer = self.config["Main Settings"]["Customers"][
                    order.account]
                soData = self.buildSOData(customer, order, vendor)
                if not test:
                    if vendor in self.vendors:
                        self.fishbowl.adjust_vendor_part_cost(order.hollander,
                                                              vendor,
                                                              order.cost)
                    elif vendor == "No Vendor":
                        self.fishbowl.importPPVP(order.hollander)
                    self.fishbowl.importSalesOrder(soData)
        if not test:
            processed_orders = []
            for vendor in self.ordersByVendor:
                for order in self.ordersByVendor[vendor]:
                    order.soNum = self.fishbowl.getSONum(order.customer_po)
                    if self.vendors.get(vendor) or vendor == "No Vendor":
                        order.poNum = self.fishbowl.getPONum(order.customer_po)
                    sbd = self._get_ship_by_date(order)
                    if sbd:
                        order.ship_by_date = sbd
                    processed_orders.append(order)
            ProcessedOrderDAO().batch_write_items(processed_orders)

    def _get_ship_by_date(self, order: Order):
        order_vendor = self.vendors.get(order.vendor)
        if order_vendor:
            ucode, status = order.hollander[PAINT_CODE_START:], order.status
            ht = order_vendor.handling_time_config.get(ucode, status)
            return str(date.today() + timedelta(days=ht))

    def getLKQStock(self):
        return self.ftpServer.get_file_as_list(
            "/lkq/Factory Wheel Warehouse_837903.csv"
        )

    def getRoadReadyStock(self):
        return self.ftpServer.get_file_as_list(
            "/roadreadywheels/roadready.csv"
        )

    def checkLKQQTY(self, partNumber):
        qty = 0
        for i in range(len(self.LKQStock)):
            if partNumber[-1] != "N":
                if self.LKQStock[i][2] in [partNumber, partNumber[:9]]:
                    qty += int(self.LKQStock[i][27])
            else:
                if self.LKQStock[i][2] == partNumber:
                    qty += int(self.LKQStock[i][27])
        return qty

    def checkRoadReadyQTY(self, partNumber):
        qty = 0
        for i in range(len(self.RRStock)):
            if partNumber[-1] != "N":
                if self.RRStock[i][2] in [partNumber, partNumber[:9]]:
                    qty += int(self.RRStock[i][27])
            else:
                if self.RRStock[i][2] == partNumber:
                    qty += int(self.RRStock[i][27])
        return qty

    def sortOrder(self, order: Order) -> None:

        """
        Checks which vendor has the wheel in stock following a specific
        order of priority.
        Order of priority: Warehouse, Coast to Coast, Perfection Wheel,
        Jante Wheel

        Keyword Arguments:
            hollander: str -> hollander to check
            qty: int -> quantity required
            sourceList: list -> list of hollanders and each vendors stock

        Return:
            Name of the vendor (str) if any else None
        """

        vendor, order.cost, order.status = self.sourceList.get_cheapest_vendor(
            order.hollander, order.qty)
        order.vendor = vendor
        if self.ordersByVendor.get(vendor):
            self.ordersByVendor[vendor].append(order)
        else:
            self.ordersByVendor[vendor] = [order]

# if __name__ == "__main__":
#     automation = InternalAutomation()
#     customer_pos = input("Enter space separated ebay order
#     numbers:\n").split()
#     tracking_numbers = {}
#     not_in_fishbowl = []
#     for customer_po in customer_pos:
#         if automation.fishbowl.isSO(customer_po):
#             tracking = automation.getTracking(customer_po)
#             if tracking:
#                 tracking_numbers[customer_po] = tracking
#         else:
#             not_in_fishbowl.append(customer_po)
#     tuple_tracking = [f"{k}: {v}" for k, v in tracking_numbers.items()]
#     tracking_numbers_formatted = "\n".join(tuple_tracking)
#     print(f"\nOrder numbers not in fishbowl: {', '.join(
#     not_in_fishbowl)}\n\n"
#           f"Orders with tracking found:\n{tracking_numbers_formatted}")
