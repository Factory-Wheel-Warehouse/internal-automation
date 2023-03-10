import datetime
import os
import re
import json
import traceback
from pypdf import PdfReader
from io import BytesIO
from dotenv import load_dotenv
import internalprocesses.aws as aws
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.inventory import Inventory
from internalprocesses.orders.address import Address
from internalprocesses.orders.orders import *
from internalprocesses.fishbowl import FishbowlClient
from internalprocesses.magentoapi.magento import MagentoConnection
from internalprocesses.outlookapi.outlook import OutlookClient
from internalprocesses.tracking import (
    get_tracking_from_outlook, TRACKING_PATTERNS, TrackingChecker
)


class InternalAutomation:

    def __init__(self):
        load_dotenv()
        self.config = self.readConfig()
        self.ordersByVendor = {}
        self.vendors = {}
        for vendor in aws.get_vendor_config_data():
            self.vendors[vendor.vendor_name] = vendor
        self.exceptionOrders = []
        self.customers = self.config["Main Settings"]["Customers"]
        self.ftpServer = self.connectFTPServer()
        self.fishbowl = self.connectFishbowl()
        self.outlook = self.connectOutlook()
        self.magento = self.connectMagento()
        self.sourceList = Inventory(list(self.vendors.values()),
                                    self.ftpServer, self.fishbowl)
        self.trackingChecker = TrackingChecker()
        self.unfulfilledOrders = self.magento.getPendingOrders()

    def close(self):

        """Closes all necessary connections."""

        self.fishbowl.close()
        self.ftpServer.close()

    def readConfig(self) -> dict:

        """Returns the loaded config.json file."""

        cd = os.path.dirname(__file__)
        configFile = os.path.join(cd, "..", "..", "data/config.json")
        return json.load(open(configFile))

    def connectFTPServer(self) -> FTPConnection:

        """Returns an FTPConnection object"""

        host = "54.211.94.170"
        username = "danny"
        password = os.getenv("FTP-PW")
        port = 21
        return FTPConnection(host, port, username, password)

    def connectFishbowl(self) -> FishbowlClient:

        """Return an instance of FishbowlClient to utilize the Fishbowl API."""

        config = self.config["APIConfig"]["Fishbowl"]
        password = os.getenv("FISHBOWL-PW")
        return FishbowlClient(
            config["Username"], password, config["Host"],
            config["Port"]
        )

    def connectOutlook(self) -> OutlookClient:

        """Returns an instance of OutlookConnection to use the Outlook API."""

        config = self.config["APIConfig"]["Outlook"]["Danny"]
        password = os.getenv("OUTLOOK-PW")
        consumerSecret = os.getenv("OUTLOOK-CS")
        return OutlookClient(config, password, consumerSecret)

    def getTracking(self, customerPO: str) -> str | None:

        """Checks for a tracking number for the customerPO passed in"""
        if self.magento.isEbayOrder(customerPO):
            customerPO = customerPO[1:]
        poNum = self.fishbowl.getPONum(customerPO)
        if poNum:
            tracking_numbers = get_tracking_from_outlook(poNum, self.outlook)
            if len(tracking_numbers) == 1:
                return list(tracking_numbers.values())[0][0]
        else:
            tracking_numbers = self.fishbowl.getTracking(customerPO)
            if tracking_numbers:
                return tracking_numbers[0]

    def checkTrackingStatus(self,
                            trackingNumber: str,
                            carrier: str,
                            customerPO: str
                            ) -> str:

        """
        Checks the tracking status of a tracking number
        """

        trackingData = self.trackingChecker.check_tracking(
            trackingNumber, carrier
        )
        if self.trackingChecker.status_code == 200:
            return trackingData["data"][0]["status"]
        else:
            self.trackingChecker.add_single_tracking(
                trackingNumber, carrier, customerPO
            )
            return self.checkTrackingStatus(
                trackingNumber, carrier, customerPO
            )

    def addTracking(self) -> None:

        """
        Adds tracking numbers to unshipped orders with available tracking
        """

        tracking = {}
        for customerPO in self.unfulfilledOrders:
            trackingNumber = self.getTracking(customerPO)
            print(customerPO, trackingNumber)
            if trackingNumber:
                tracking[customerPO] = trackingNumber
        for customerPO, trackingNumber in tracking.items():
            if not self.magento.isAmazonOrder(customerPO):
                # Should delete after adding, but delete request keeps 
                # returning server error for some reason
                print(customerPO, trackingNumber)
                self.magento.addOrderTracking(customerPO, trackingNumber)
            else:
                carrier = self.magento.getCarrier(trackingNumber)
                status = self.checkTrackingStatus(
                    trackingNumber, carrier, customerPO
                )
                if status == "transit":
                    self.magento.addOrderTracking(customerPO, trackingNumber)

    def connectMagento(self) -> MagentoConnection:
        accessToken = os.getenv("MAGENTO-AT")
        return MagentoConnection(accessToken)

    def buildSOItemString(self, order: str, vendor: str) -> str:

        """
        Takes in an Order object and builds the row to be used in the Fishbowl 
        import for the item ordered.

        Keyword Argument:

            order: Order
                customer order being processed

        Return:

            str : formatted row describing the item
        """

        itemType = 10
        if vendor != "Warehouse":
            itemType = 12
        string = f'"Item", {itemType}, "{order.hollander}", , {order.qty}, '
        string += f'"ea", {order.price}, , , , , , , , , '
        return string

    def buildSOString(self, customer: str, order: str) -> str:

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
        string += f'"UPS", "None", 30, "{order.customerPO}"'
        return string

    def buildSOData(self, customer: str, order: str, vendor: str) -> list[str]:

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

        return [
            self.buildSOString(customer, order),
            self.buildSOItemString(order, vendor)
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

        itemType = 10
        item_data = ["Item", itemType, order.hollander, order.hollander,
                     order.hollander, order.qty, "ea", 0]
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
            po_data = ["PO", order.poNum, "20", vendor.address.name, "",
                       vendor.address.name, vendor.address.street,
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
        address = Address(
            " ".join([shipping["firstname"], shipping["lastname"]]),
            shipping["street"][0],
            shipping["city"], shipping["region_code"],
            shipping["postcode"]
        )
        if len(shipping["street"]) == 2:
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
            if sku:
                return Order(
                    address, sku, item["qty_ordered"],
                    item["price"], customerPO=orderID
                )
        if self.magento.isEbayOrder(orderID):
            orderID = orderID[1:]
        if not self.fishbowl.isSO(orderID):
            self.exceptionOrders.append(
                f"Order #{orderID}\n\n"
            )

    def setOrderType(self, order: Order) -> None:

        if self.magento.isAmazonOrder(order.customerPO):
            order.__class__ = AmazonOrder
            order.avenue = "Amazon"
        elif self.magento.isWalmartOrder(order.customerPO):
            order.__class__ = WalmartOrder
            order.avenue = "Walmart"
        elif self.magento.isWebsiteOrder(order.customerPO):
            order.__class__ = WebsiteOrder
            order.avenue = "Website"
        elif self.magento.isEbayOrder(order.customerPO):
            ebayAccount = self.magento.getEbayAccount(order.customerPO)
            order.customerPO = order.customerPO[1:]
            if ebayAccount == "Main Ebay":
                order.__class__ = MainEbayOrder
                order.avenue = "Main Ebay"
            elif ebayAccount == "Ebay Albany":
                order.__class__ = EbayAlbanyOrder
                order.avenue = "Ebay Albany"
            elif ebayAccount == "OED":
                order.__class__ = OEDOrder
                order.avenue = "OED"

    def readMagentoOrders(self) -> None:
        for orderID in self.unfulfilledOrders:
            orderDetails = self.magento.getOrderDetails(orderID)
            address = self.getMagentoAddress(orderDetails)
            order = self.buildMagentoOrder(orderDetails, orderID, address)
            if order:
                self.setOrderType(order)
                if not self.fishbowl.isSO(order.customerPO):
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

    def importSalesOrders(self):

        """
        Returns formatted orders coming from a specified vendor for import.
        
        Keyword Arguments:

            venodr : str
                vendor of the orders being processed

        Return:

            dict : json response to import
        """

        soData = []
        for vendor in self.ordersByVendor:
            if vendor != ["No vendor"]:
                for order in self.ordersByVendor[vendor]:
                    if not self.fishbowl.isProduct(order.hollander):
                        self.fishbowl.importProduct(order.hollander)
                        # set default vendor as coast
                    customer = self.config["Main Settings"] \
                        ["Customers"][order.avenue]
                    soData += self.buildSOData(customer, order, vendor)
        response = self.fishbowl.importSalesOrder(soData)
        for vendor in self.ordersByVendor:
            for order in self.ordersByVendor[vendor]:
                order.soNum = self.fishbowl.getSONum(order.customerPO)
                if vendor != "Warehouse":
                    poNum = self.fishbowl.getPONum(order.customerPO)
                    order.poNum = poNum
        return response

    def importPurchaseOrders(self):

        """Formats purchase orders for a specific vendor."""

        poData = []
        for vendor in self.ordersByVendor:
            if self.ordersByVendor[vendor] and vendor in self.vendors:
                for order in self.ordersByVendor[vendor]:
                    poData += self.buildPOData(vendor, order)
        response = self.fishbowl.importPurchaseOrder(poData)
        return response

    def importOrders(self):

        """Sends an import request to import all pending sales."""

        self.importSalesOrders()
        self.importPurchaseOrders()

    def getLKQStock(self):
        return self.ftpServer.getFileAsList(
            "/lkq/Factory Wheel Warehouse_837903.csv"
        )

    def getRoadReadyStock(self):
        return self.ftpServer.getFileAsList(
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

    def sortOrder(self, order) -> None:

        """
        Checks which vendor has the wheel in stock following a specific order of priority.
        Order of priority: Warehouse, Coast to Coast, Perfection Wheel, Jante Wheel

        Keyword Arguments:
            hollander: str -> hollander to check
            qty: int -> quantity required
            sourceList: list -> list of hollanders and each vendors stock

        Return:
            Name of the vendor (str) if any else None
        """

        vendor = self.sourceList.get_cheapest_vendor(order.hollander,
                                                     order.qty)
        if not vendor:
            vendor = "No vendor"
        if self.ordersByVendor.get(vendor):
            self.ordersByVendor[vendor].append(order)
        else:
            self.ordersByVendor[vendor] = [order]


def orderImport(test=True):
    start = datetime.datetime.now()
    automation = InternalAutomation()
    try:
        automation.getOrders()
        if not test:
            automation.importOrders()
            email = "sales@factorywheelwarehouse.com"
        else:
            email = "danny@factorywheelwarehouse.com"
        for vendor in automation.ordersByVendor:
            automation.emailDropships(automation.ordersByVendor[vendor],
                                      vendor, email)
        automation.emailExceptionOrders(email)
    except Exception:
        traceback.print_exc()
    print((datetime.datetime.now() - start).total_seconds())


def trackingUpload():
    automation = InternalAutomation()
    try:
        automation.addTracking()
    except Exception:
        traceback.print_exc()
