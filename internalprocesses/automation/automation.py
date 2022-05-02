import os
import re
import json
import traceback
from dotenv import load_dotenv
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.wheelsourcing import wheelsourcing
from internalprocesses.orders.address import Address
from internalprocesses.orders.orders import AmazonOrder, EbayAlbanyOrder, FacebookOrder, \
    MainEbayOrder, Order, WalmartOrder, WebsiteOrder
from internalprocesses.shopifyapi.shopify import ShopifyConnection
from internalprocesses.fishbowlclient.fishbowl import FBConnection
from internalprocesses.magentoapi.magento import MagentoConnection
from internalprocesses.outlookapi.outlook import OutlookConnection
from internalprocesses.tracktry.tracker import TrackingChecker

class InternalAutomation():

    def __init__(self):
        load_dotenv()
        self.config = self.readConfig()
        self.ordersByVendor = {
            "Warehouse" : [],
            "Coast" : [],
            "Perfection" : [],
            "Jante" : [],
            "Road Ready": [],
            "Blackburns" : [],
            "No vendor" : []
        }
        self.exceptionOrders = []
        self.customers = self.config["Main Settings"]["Customers"]
        self.ftpServer = self.connectFTPServer()
        self.fishbowl = self.connectFishbowl()
        self.outlook = self.connectOutlook()
        self.facebook = self.connectFacebook()
        self.magento = self.connectMagento()
        self.sourceList = wheelsourcing.buildVendorInventory(
            self.ftpServer, self.fishbowl
        )
        self.trackingChecker = TrackingChecker()
        self.unfulfilledOrders = self.magento.getPendingOrders()

    def close(self):

        """Closes all necessary connections."""

        self.fishbowl.close()
        self.ftpServer.close()

    def readConfig(self):

        """Returns the loaded config.json file."""

        cd = os.path.dirname(__file__)
        configFile= os.path.join(cd, "..", "..", "data/config.json")
        return json.load(open(configFile))

    def connectFTPServer(self):
        host = "54.211.94.170"
        username = "danny"
        password = os.getenv("FTP-PW")
        port = 21
        return FTPConnection(host, port, username, password)

    def connectFishbowl(self):

        """Return an instance of FBConnection to utilize the Fishbowl API."""

        config = self.config["APIConfig"]["Fishbowl"]
        password = os.getenv("FISHBOWL-PW")
        return FBConnection(
            config["Username"], password, config["Host"],
            config["Port"]
        )
    
    def connectOutlook(self):

        """Returns an instance of OutlookConnection to use the Outlook API."""

        config = self.config["APIConfig"]["Outlook"]["Danny"]
        password = os.getenv("OUTLOOK-PW")
        consumerSecret = os.getenv("OUTLOOK-CS")
        return OutlookConnection(config, password, consumerSecret)

    def getCoastTracking(self, poNum):
        """
        Searches the connected outlook address for an email from coast to 
        coast containing the order tracking number
        """
        searchQuery = f'?$search="body:Customer P/O {poNum} Tracking"'
        email = self.outlook.searchMessages(searchQuery)
        if email:
            body = email["body"]["content"]
            # Mark as read
            return re.findall(r"1Z[a-z|A-Z|0-9]{8}[0-9]{8}", body)[0]
        
    def getJanteTracking(self, poNum):
        """
        Searches the connected outlook address for an email from jante wheels
        containing the order invoice and tracking number
        """
        searchQuery = f'?$search="subject: New Invoice - Customer PO {poNum}"'
        email = self.outlook.searchMessages(searchQuery)
        if email:
            body = email["body"]["content"]
            # Mark as read
            return re.findall(r"[0-9]{12}", body)[0]

    def getPerfectionTracking(self, poNum):
        searchQuery = '?$search="subject:UPS Ship Notification, Tracking '
        searchQuery += f'Number AND body:{poNum}"'
        email = self.outlook.searchMessages(searchQuery)
        if email:
            body = email["body"]["content"]
            # Mark as read
            return re.findall(r"1Z[a-z|A-Z|0-9]{8}[0-9]{8}", body)[0]

    def getBlackburnsTracking(self, poNum):
        searchQuery = '?$search="subject:FedEx Shipment '
        searchQuery += f'AND body:{poNum}"'
        email = self.outlook.searchMessages(searchQuery)
        if email:
            body = email["body"]["content"]
            # Mark as read
            return re.findall(r"[0-9]{12}", body)[0]

    def getTracking(self, customerPO):
        """Checks for a tracking number for the customerPO passed in"""
        if self.magento.isEbayOrder(customerPO):
            customerPO = customerPO[1:]
        poNum = self.fishbowl.getPONum(customerPO)
        if poNum:
            return self.trackingNumberSearch(poNum)
        else:
            return self.fishbowl.getTracking(customerPO)

    def checkTrackingStatus(self, trackingNumber, carrier, customerPO):
        trackingData = self.trackingChecker.checkTracking(
            trackingNumber, carrier
        )
        if self.trackingChecker.statusCode == 200:
            return trackingData["data"][0]["status"]
        else:
            self.trackingChecker.addSingleTracking(
                trackingNumber, carrier, customerPO
            )
            return self.checkTrackingStatus(
                trackingNumber, carrier, customerPO
            )

    def addTracking(self):
        tracking = {}
        for customerPO in self.unfulfilledOrders:
            trackingNumber = self.getTracking(customerPO)
            if trackingNumber:
                tracking[customerPO] = trackingNumber
        for customerPO, trackingNumber in tracking.items():
            if not self.magento.isAmazonOrder(customerPO):
                # Should delete after adding, but delete request keeps 
                # returning server error for some reason
                self.magento.addOrderTracking(customerPO, trackingNumber)
            else:
                carrier = self.magento.getCarrier(trackingNumber)
                status = self.checkTrackingStatus(
                    trackingNumber, carrier, customerPO
                )
                if status == "transit":
                    self.magento.addOrderTracking(customerPO, trackingNumber)

    def trackingNumberSearch(self, poNum):
        trackingNum = self.getCoastTracking(poNum)
        if not trackingNum:
            trackingNum = self.getJanteTracking(poNum)
        if not trackingNum:
            trackingNum = self.getPerfectionTracking(poNum)
        if not trackingNum:
            trackingNum = self.getBlackburnsTracking(poNum)
        return trackingNum

    def connectFacebook(self):

        """ Connects to the shopify API to manage Facebook Orders """
        password = os.getenv("SHOPIFY-PW")
        apiKey = os.getenv("SHOPIFY-APIKEY")
        config = self.config["APIConfig"]["Shopify"]
        return ShopifyConnection(config, password, apiKey)

    def connectMagento(self):
        accessToken = os.getenv("MAGENTO-AT")
        return MagentoConnection(accessToken)

    def buildSOItemString(self, order, vendor):

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

    def buildSOString(self, customer, order):

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

    def buildSOData(self, customer, order, vendor):
        
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

    def buildPOItemString(self, order):

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
        string = f'"Item", {itemType}, "{order.hollander}", '
        string += f'"{order.hollander}", {order.qty}, "ea", 0'
        return string

    def buildPOString(self, vendor, order):

        """
        Takes in Order object and vendor (really dropshipper) and builds 
        the row describing the purchase order.

        Keyword Arguments:

            vendor : dict
                dictionary describing the customer as defined in config.json
            
            order: Order
                order object being processed
            
        Return:

            str: formatted row describing the sales order
        """

        string = f'"PO", {order.poNum}, 20, "{vendor["Name"]}", , '
        string += f'"{vendor["Name"]}", ""{vendor["Address"]}"", '
        string += f'"{vendor["City"]}","{vendor["State"]}", '
        string += f'"{vendor["Zipcode"]}", "{vendor["Country"]}", '
        string += f'"{order.address.name}", '
        string += rf'"{order.address.name}", "{order.address.street}", '
        string += f'"{order.address.city}", "{order.address.state}", '
        string += f'"{order.address.zipcode}", "United States", "UPS"'
        return string

    def buildPOData(self, vendor, order):

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

    def getFacebookAddress(self, orderDetails):
        
        shipping = orderDetails["shipping_address"]
        address = Address(
            shipping["name"], shipping["address1"], 
            shipping["city"], shipping["province_code"], 
            shipping["zip"]
        )
        if shipping["address2"]:
            address.street2 = shipping["address2"]
        return address

    def buildFacebookOrder(self, orderDetails):
        
        lineItems = orderDetails["line_items"]
        if lineItems and len(lineItems) == 1:
            item = lineItems[0]
            address = self.getFacebookAddress(orderDetails)
            return FacebookOrder(
                address, item["sku"], item["quantity"], float(item["price"]),
                customerPO = orderDetails["note_attributes"][1]["value"]
            )

    def getMagentoAddress(self, orderDetails):
        shipping = orderDetails["extension_attributes"]\
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

    def checkForValidSKU(self, sku):
        pattern = r'(ALY|STL)[0-9]{5}[A-Z]{1}[0-9]{2}[N]?'
        search = re.search(pattern, sku.upper())
        if search:
            return search.group()

    def buildMagentoOrder(self, orderDetails, orderID, address):
        lineItems = orderDetails["items"]
        if lineItems and len(lineItems) == 1:
            item = lineItems[0]
            sku = self.checkForValidSKU(item["sku"])
            if not sku:
                sku = self.checkForValidSKU(item["name"])
            if sku:
                return Order(
                    address, sku, item["qty_ordered"], 
                    item["price"], customerPO = orderID
                )
        if self.magento.isEbayOrder(orderID):
            orderID = orderID[1:]
        if not self.fishbowl.isSO(orderID):
            self.exceptionOrders.append(
                f"Order #{orderID}\n\n"
            )

    def readFacebookOrders(self):

        """ Reads in facebook orders using the shopify API connection """
        
        orderIDs = self.facebook.getPendingOrders()
        processedOrderIDs = []
        for orderID in orderIDs:
            orderDetails = self.facebook.getOrderDetails(orderID)
            lineItems = orderDetails["line_items"]
            if lineItems and len(lineItems) == 1:
                order = self.buildFacebookOrder(orderDetails)
                if (order.customerPO not in processedOrderIDs and not
                self.fishbowl.isSO(order.customerPO)):
                    self.sortOrder(order)
                    processedOrderIDs.append(order.customerPO)

    def setOrderType(self, order):

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

    def readMagentoOrders(self):

        for orderID in self.unfulfilledOrders:
            orderDetails = self.magento.getOrderDetails(orderID)
            address = self.getMagentoAddress(orderDetails)
            order = self.buildMagentoOrder(orderDetails, orderID, address)
            if order:
                self.setOrderType(order)
                if not self.fishbowl.isSO(order.customerPO):
                    self.sortOrder(order)

    def getOrders(self):

        """Organizes orders from each selling avenue into ordersByVendor."""

        self.readMagentoOrders()
        self.readFacebookOrders()
    
    def emailDropships(self, orders, vendor, emailAddress):

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

    def emailExceptionOrders(self, emailAddress):
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
                    customer = self.config["Main Settings"]\
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
            if (self.ordersByVendor[vendor] and vendor != "Warehouse" and 
            vendor != "No vendor"):
                for order in self.ordersByVendor[vendor]:
                    vendorDetails = self.config["Main Settings"]["Vendors"]\
                        [vendor]
                    poData += self.buildPOData(vendorDetails, order)
        response = self.fishbowl.importPurchaseOrder(poData)
        return response

    def importOrders(self):

        """Sends an import request to import all pending sales."""

        self.importSalesOrders()
        self.importPurchaseOrders()

    def generateSourceList(self) -> list:
        
        """
        Modify to pull Sams most recent email!
        """
        """
        Returns the inventory file conatining vendor inventory as a list.

        Return:
            list : inventory by vendor
        """

        sourceListText = self.outlook.getSourceList().text
        sourceList = [row.strip("\r") for row in sourceListText.split("\n")]
        for i in range(len(sourceList) - 1):
            sourceList[i] = sourceList[i].split(",")
        sourceList.pop(len(sourceList) - 1)
        return sourceList

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
        
        vendor = wheelsourcing.assignCheapestVendor(
            order.hollander, order.qty, self.sourceList, order.avenue
        )
        if not vendor:
            vendor = "No vendor"
        self.ordersByVendor[vendor].append(order)

def orderImport(test = True):
    automation = InternalAutomation()
    try:
        automation.getOrders()
        if not test:
            automation.importOrders()
        for vendor in automation.ordersByVendor:
            if automation.ordersByVendor[vendor] and not test:
                automation.emailDropships(
                    automation.ordersByVendor[vendor], vendor, 
                    "sales@factorywheelwarehouse.com"
                )
                automation.emailExceptionOrders(
                    "sales@factorywheelwarehouse.com"
                )
            if automation.ordersByVendor[vendor] and test:
                automation.emailDropships(
                    automation.ordersByVendor[vendor], vendor, 
                    "danny@factorywheelwarehouse.com"
                )
                automation.emailExceptionOrders(
                    "danny@factorywheelwarehouse.com"
                )
        print(automation.ordersByVendor)
        print(automation.exceptionOrders)
    except Exception:
        print(traceback.print_exc())
    finally:
        automation.close()

def trackingUpload():
    automation = InternalAutomation()
    try:
        automation.addTracking()
    except Exception:
        print(traceback.print_exc())
    finally:
        automation.close()

if __name__ == "__main__":
    print("Imports Successful!")