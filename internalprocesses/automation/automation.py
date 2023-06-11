import re
import json
from dotenv import load_dotenv
from internalprocesses.automation.constants import *
from internalprocesses.aws.dynamodb import ProcessedOrderDAO, InventoryDAO, \
    VendorConfigDAO
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.inventory import Inventory
from internalprocesses.orders.orders import *
from internalprocesses.fishbowl import FishbowlClient
from internalprocesses.magentoapi.magento import MagentoConnection
from internalprocesses.outlookapi.outlook import OutlookClient
from internalprocesses.tracking import (
    get_tracking_from_outlook, TrackingChecker
)


class InternalAutomation:

    def __init__(self):
        load_dotenv()
        self.config = self.readConfig()
        self.ordersByVendor = {}
        self.vendors = {}
        for vendor in VendorConfigDAO().get_all_items():
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
                trackingNumber, carrier, customer_po
            )
            return self.checkTrackingStatus(
                trackingNumber, carrier, customer_po
            )

    def add_tracking_number_and_fulfill(self, customer_po, tracking_number,
                                        po, zero_cost_pos) -> None:
        self.magento.addOrderTracking(customer_po,
                                      tracking_number)
        if po:
            try:
                if not self.fishbowl.fulfill_po(po):
                    zero_cost_pos.append(po)
            except:
                print(f"{po} already fulfilled")

    def addTracking(self) -> None:

        """
        Adds tracking numbers to unshipped orders with available tracking
        """

        tracking = {}
        for customer_po in self.unfulfilledOrders:
            trackingNumber = None
            try:
                trackingNumber = self.getTracking(customer_po)
            except KeyError:
                print(f"KeyError searching for tracking:\nCustomerPO: "
                      f"{customer_po}")
            if trackingNumber:
                tracking[customer_po] = trackingNumber
        zero_cost_pos = []
        for customer_po, trackingNumber in tracking.items():
            if customer_po[0].isalpha():
                po = self.fishbowl.getPONum(customer_po[1:])
            else:
                po = self.fishbowl.getPONum(customer_po)
            if not self.magento.isAmazonOrder(customer_po):
                self.add_tracking_number_and_fulfill(customer_po,
                                                     trackingNumber, po,
                                                     zero_cost_pos)
            else:
                carrier = self.magento.getCarrier(trackingNumber)
                status = self.checkTrackingStatus(
                    trackingNumber, carrier, customer_po
                )
                if status in ["transit", "pickup", "delivered"]:
                    self.add_tracking_number_and_fulfill(customer_po,
                                                         trackingNumber, po,
                                                         zero_cost_pos)
        if zero_cost_pos:
            self.outlook.sendMail("sales@factorywheelwarehouse.com",
                                  "Unfulfilled POs with Tracking Received",
                                  "The following POs have had tracking "
                                  "uploaded but had zero cost PO items:\n\n"
                                  f"{zero_cost_pos}")

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
        string += f'"UPS", "None", 30, "{order.customer_po}"'
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
                    "account": account
                }
                return Order(**order)
        if not self.fishbowl.isSO(orderID):
            self.exceptionOrders.append(
                f"Order #{orderID}\n\n"
            )

    def readMagentoOrders(self) -> None:
        for orderID in self.unfulfilledOrders:
            orderDetails = self.magento.getOrderDetails(orderID)
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

    def importOrders(self):

        """Sends an import request to import all pending sales."""

        for vendor in self.ordersByVendor:
            for order in self.ordersByVendor[vendor]:
                if not self.fishbowl.isProduct(order.hollander):
                    self.fishbowl.importProduct(order.hollander)
                customer = self.config["Main Settings"]["Customers"][
                    order.account]
                soData = self.buildSOData(customer, order, vendor)
                if vendor in self.vendors:
                    self.fishbowl.adjust_vendor_part_cost(order.hollander,
                                                          vendor, order.cost)
                self.fishbowl.importSalesOrder(soData)

        processed_orders = []
        processed_order_count = 0
        for vendor in self.ordersByVendor:
            for order in self.ordersByVendor[vendor]:
                order.soNum = self.fishbowl.getSONum(order.customer_po)
                if self.vendors.get(vendor) or vendor == "No Vendor":
                    order.poNum = self.fishbowl.getPONum(order.customer_po)
                sbd = InventoryDAO().get_ship_by_date(order)
                if sbd:
                    order.ship_by_date = sbd
                    order.vendor = vendor
                    processed_orders.append(order)
                    processed_order_count += 1
        ProcessedOrderDAO().batch_write_items(processed_orders,
                                              processed_order_count)

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
        Checks which vendor has the wheel in stock following a specific order of priority.
        Order of priority: Warehouse, Coast to Coast, Perfection Wheel, Jante Wheel

        Keyword Arguments:
            hollander: str -> hollander to check
            qty: int -> quantity required
            sourceList: list -> list of hollanders and each vendors stock

        Return:
            Name of the vendor (str) if any else None
        """

        vendor, order.cost = self.sourceList.get_cheapest_vendor(
            order.hollander, order.qty)
        print(vendor)
        if self.ordersByVendor.get(vendor):
            self.ordersByVendor[vendor].append(order)
        else:
            self.ordersByVendor[vendor] = [order]
