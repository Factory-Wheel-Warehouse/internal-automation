import socket
import json
import struct
from base64 import b64encode as b64
from hashlib import md5


class FishbowlClient:
    """
    Class for facilitating interaction with the Fishbowl API.

    Attributes
    ----------
    username : str
        username of the account to log in as

    password : str
        password of the account

    host : str
        IPv4 address or domain of Fishbowl server

    port : int
        port that Fishbowl server is utilizing

    key : str
        access key granted by Fishbowl API

    statusCode : int
        status code returned from latest request to Fishbowl API (1000 meaning
        the request succeeded and there are no issues)

    statusDescription : str 
        brief description of the statusCode as defined in the Fishbowl API
        documentation
    
    Methods
    -------

    """

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, username):
        self._username = username

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        self._password = password

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, host):
        self._host = host

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        self._port = port

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        self._key = key

    @property
    def statusCode(self):
        return self._statusCode

    @statusCode.setter
    def statusCode(self, statusCode):
        self._statusCode = statusCode

    @property
    def statusDescription(self):
        return self._statusDescription

    @statusDescription.setter
    def statusDescription(self, statusDescription):
        self._statusDescription = statusDescription

    def __init__(self, username, password, host, port=28192):

        """
        Initializes the connection to the Fishbowl API by setting properties
        and sending the initial login request.

        Keyword Arguments:

            username : str 
                username of the account to connect as

            password : str
                password of the account to connect as
            
            host : str
                IPv4 address or domain of the Fishbowl Server host
        
        Default Argument:

            port : int (Default: 28192)
                port that Fishbowl Server is utilizing 
        """

        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.key = ""
        self.connect()
        self.loginRequest()

    def __del__(self):
        self.close()

    def connect(self):

        """Initializes a socket and connects to the host and port."""

        self.stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.stream.connect((self.host, self.port))
        self.stream.settimeout(10)

    def close(self):

        """
        Closes the fishbowl connection by sending a logout request to the
        Fishbowl API and the closing the socket.
        """
        if self.statusCode != 1162:
            self.logoutRequest()
            self.stream.shutdown(2)
            self.stream.close()

    def getResponseLength(self):

        """Returns the length of the response received from the API."""

        packedLength = self.stream.recv(4)
        length = struct.unpack(">L", packedLength)
        return length[0]

    def getResponseMessage(self, length):

        """
        Returns the message in the response received from the API.

        Keyword Arguments:

            length : int
                length of the response received
        """

        messageRecv = ""
        bytesRecv = 0
        while bytesRecv < length:
            byte = self.stream.recv(1)
            bytesRecv += 1
            messageRecv += byte.decode()
        return messageRecv

    def getResponse(self):

        """Gets length of response and uses it to return the message."""

        length = self.getResponseLength()
        response = self.getResponseMessage(length)
        return response

    def parseResponse(self, jsonResponse):
        return json.loads(jsonResponse)

    def prepMessage(self, jsonDict):

        """Returns the message after preparing for sending."""

        request = json.dumps(jsonDict).encode()
        length = len(request)
        packedLength = struct.pack(">L", length)
        message = packedLength + request
        return message

    def sendRequest(self, jsonDict):

        """
        Formats and sends a request with the specified body.

        Keyword Arguments:

            jsonDict : dict
                specific request to send the the API
        
        Return:

            dict : response received from the API
        """

        message = self.prepMessage(jsonDict)
        self.stream.send(message)
        responseString = self.getResponse()
        responseJson = self.parseResponse(responseString)
        self.setStatus(responseJson["FbiJson"]["FbiMsgsRs"]["statusCode"])
        return responseJson

    def loginRequest(self):

        """Sends a request to login and sets the access key."""

        jsonDict = {
            "FbiJson": {
                "Ticket": {
                    "Key": ""
                },
                "FbiMsgsRq": {
                    "LoginRq": {
                        "IAID": 4444,
                        "IAName": "Internal Process Automation",
                        "IADescription": "Automation of internal processes.",
                        "UserName": self.username,
                        "UserPassword": self.password
                    }
                }
            }
        }
        response = self.sendRequest(jsonDict)
        if self.statusCode == 1000:
            self.key = response["FbiJson"]["Ticket"]["Key"]
        else:
            status = {
                "code": str(self.statusCode),
                "description": str(self.statusDescription)
            }
            self.close()
            raise Exception(f"{status}")

    def logoutRequest(self):

        """Sends the request to logout."""

        jsonDict = {
            "FbiJson": {
                "Ticket": {
                    "Key": self.key
                },
                "FbiMsgsRq": {
                    "LogoutRq": ""
                }
            }
        }
        self.sendRequest(jsonDict)

    def testKey(self):
        jsonDict = {
            "FbiJson": {
                "Ticket": {
                    "Key": self.key
                },
                "FbiMsgsRq": {
                    "IssueSORq": {
                        "SONumber": "60000"
                    }
                }
            }
        }
        self.sendRequest(jsonDict)

    def sendImportRequest(self, data, importType):

        """
        Formats an import request given the csv rows and sends the request to
        the API.

        Keyword Arguments: 

            data : List[str]
                data as a list where each element is an entire row
            
            importType : str
                type of import being performed
        
        Return: 

            dict : response received
        """

        jsonDict = {
            "FbiJson": {
                "Ticket": {
                    "Key": self.key
                },
                "FbiMsgsRq": {
                    "ImportRq": {
                        "Type": importType,
                        "Rows": {
                            "Row": data
                        }
                    }
                }
            }
        }
        response = self.sendRequest(jsonDict)
        return response

    def importPart(self, partNumber):

        """Adds a list of parts into Fishbowl and returns the response."""

        data = [
            '"PartNumber", "PartDescription", "UOM", "PartType", ' \
            '"POItemType", "ConsumptionRate"',
        ]
        data.append(
            f'"{partNumber}", "{partNumber}", "ea", "Inventory", "Purchase", 0'
        )
        response = self.sendImportRequest(data, "ImportPart")
        self.importPPVP(partNumber)
        return response

    def importPPVP(self, partNumber):

        """Creates a default vendor for a newly added part"""

        data = [
            '"PartNumber", "ProductNumber", "Vendor", "DefaultVendor", ' \
            '"VendorPartNumber", "Cost"'
        ]
        data.append(
            f'"{partNumber}", "{partNumber}", "Coast to Coast", ' \
            '"true", "{partNumber}", 0'
        )
        response = self.sendImportRequest(
            data, "ImportPartProductAndVendorPricing"
        )
        return response

    def importProduct(self, productNumber):

        """Adds a list of products into Fishbowl and returns the response."""

        self.importPart(productNumber)
        data = ['"PartNumber", "ProductNumber"']
        data.append(f'"{productNumber}", "{productNumber}"')
        response = self.sendImportRequest(data, "ImportProduct")
        return response

    def importSalesOrder(self, soData):

        """Adds a sales order into Fishbowl."""

        data = [
            '"Flag", "SONum", "Status", "CustomerName", "CustomerContact", "BillToName", "BillToAddress", "BillToCity", "BillToState", "BillToZip", "BillToCountry", "ShipToName", "ShipToAddress", "ShipToCity", "ShipToState", "ShipToZip", "ShipToCountry", "ShipToResidential", "CarrierName", "TaxRateName", "PriorityId", "PONum"',
            '"Flag", "SOItemTypeID", "ProductNumber", "ProductDescription", "ProductQuantity", "UOM", "ProductPrice", "Taxable", "TaxCode", "Note", "ItemQuickBooksClassName", "ItemDateScheduled", "ShowItem", "KitItem", "RevisionLevel", "CustomerPartNumber"'
        ]
        data += soData
        response = self.sendImportRequest(data, "ImportSalesOrder")
        return response

    def importPurchaseOrder(self, poData):

        """Adds a purchase order into Fishbowl."""

        data = [
            '"Flag", "PONum", "Status", "VendorName", "VendorContact", "RemitToName", "RemitToAddress", "RemitToCity", "RemitToState", "RemitToZip", "RemitToCountry", "ShipToName", "DeliverToName", "ShipToAddress", "ShipToCity", "ShipToState", "ShipToZip", "ShipToCountry", "CarrierName"',
            '"Flag", "POItemTypeID", "PartNumber", "VendorPartNumber", "PartQuantity", "UOM", "PartPrice"'
        ]
        data += poData
        response = self.sendImportRequest(data, "ImportPurchaseOrder")
        return response

    def sendQueryRequest(self, query):

        """Sends a query request to the API and returns its response."""

        jsonDict = {
            "FbiJson": {
                "Ticket": {
                    "Key": self.key
                },
                "FbiMsgsRq": {
                    "ExecuteQueryRq": {
                        "Query": query
                    }
                }
            }
        }
        return self.sendRequest(jsonDict)

    def hasResult(self, query):

        """Returns True if a query has results, else False."""

        response = self.sendQueryRequest(query)
        resultsCount = response["FbiJson"]["FbiMsgsRs"]["ExecuteQueryRs"] \
            ["Rows"]["Row"][1].strip('"')
        if int(resultsCount) > 0:
            return True
        return False

    def checkProductQTY(self, hollander):
        query = f"SELECT SUM(QTY) FROM PART, QOHVIEW WHERE (PART.num = "
        query += f"'{hollander}' OR PART.num LIKE '{hollander[:9]}__*CORE')"
        query += f" AND Part.id = QOHVIEW.PARTID "
        query += "AND (QOHVIEW.LOCATIONID BETWEEN 612 AND 1053 OR "
        query += "QOHVIEW.LOCATIONID BETWEEN 1062 AND 1477);"
        response = self.sendQueryRequest(query)
        qty = response["FbiJson"]["FbiMsgsRs"]["ExecuteQueryRs"] \
            ["Rows"]["Row"][1]
        if qty:
            return int(float(qty.strip('"')) // 1)

    def isProduct(self, productNumber):

        """Checks if a product is in Fishbowl"""

        query = f'SELECT COUNT(id) FROM product\
            WHERE product.num = "{productNumber}"'
        return self.hasResult(query)

    def isSO(self, customerPO):

        """Checks if a sales order is in fishbowl by customer PO."""

        query = f'SELECT COUNT(id) FROM so\
            WHERE so.customerPO = "{customerPO}"'
        return self.hasResult(query)

    def getSONum(self, customerPO):

        """Returns the SO number of a given customerPO"""

        query = f'SELECT num FROM so WHERE so.customerPO = "{customerPO}"'
        response = self.sendQueryRequest(query)
        soNum = response["FbiJson"]["FbiMsgsRs"]["ExecuteQueryRs"] \
            ["Rows"]["Row"][1]
        if len(soNum) > 1:
            return soNum.strip('"')

    def getPONum(self, customerPO):

        """Returns the SO number of a given customerPO"""

        query = f'SELECT vendorPO FROM so WHERE so.customerPO = "{customerPO}"'
        response = self.sendQueryRequest(query)
        poNum = response["FbiJson"]["FbiMsgsRs"]["ExecuteQueryRs"] \
            ["Rows"]["Row"][1]
        if len(poNum) > 1:
            return poNum.strip('"')

    def getCustomerPO(self, soNum):
        query = f'SELECT customerPO FROM so WHERE so.num = "{soNum}"'
        response = self.sendQueryRequest(query)
        poNum = response["FbiJson"]["FbiMsgsRs"]["ExecuteQueryRs"] \
            ["Rows"]["Row"][1]
        if len(poNum) > 1:
            return poNum.strip('"')

    def getTracking(self, customerPO):
        soNum = self.getSONum(customerPO)
        query = f"""
        SELECT id 
        FROM ship 
        WHERE ship.num = "S{soNum}"
        """
        response = self.sendQueryRequest(query)
        shipID = response["FbiJson"]["FbiMsgsRs"]["ExecuteQueryRs"] \
            ["Rows"]["Row"][1].strip('"')
        if shipID:
            query = f"""
            SELECT trackingNum 
            FROM shipcarton 
            WHERE shipcarton.shipId = "{shipID}"
            """
            response = self.sendQueryRequest(query)
            tracking_numbers = response["FbiJson"]["FbiMsgsRs"][
                                   "ExecuteQueryRs"]["Rows"]["Row"][1:]
            if len(shipID) > 1:
                return [number.strip('"') for number in tracking_numbers]

    def getPartsOnHand(self):
        query = "SELECT STOCK.NUM, STOCK.QTY, PARTCOST.avgCost "
        query += "FROM ( "
        query += "    SELECT PART.id as id, PART.num as NUM, QOHVIEW.QTY as QTY "
        query += "    FROM QOHVIEW "
        query += "    LEFT JOIN PART "
        query += "    ON QOHVIEW.PARTID = PART.id "
        query += "    WHERE QOHVIEW.QTY > 0 "
        query += "    AND ( "
        query += "        QOHVIEW.LOCATIONID BETWEEN 612 AND 1053 "
        query += "        OR QOHVIEW.LOCATIONID BETWEEN 1062 AND 1477 "
        query += "    )"
        query += ") as STOCK "
        query += "LEFT JOIN PARTCOST "
        query += "ON STOCK.id = PARTCOST.id; "
        response = self.sendQueryRequest(query)
        return response["FbiJson"]["FbiMsgsRs"]["ExecuteQueryRs"] \
            ["Rows"]["Row"]

    def setStatus(self, statusCode):

        if statusCode == 900:
            description = "Success! This API request is deprecated and could be removed in the future."
        elif statusCode == 1000:
            description = "Success!"
        elif statusCode == 1001:
            description = "Unknown message received."
        elif statusCode == 1002:
            description = "Connection to Fishbowl server was lost."
        elif statusCode == 1003:
            description = "Some requests had errors."
        elif statusCode == 1004:
            description = "There was an error with the database."
        elif statusCode == 1009:
            description = "Fishbowl server has been shut down."
        elif statusCode == 1010:
            description = "You have been logged off the server by an administrator."
        elif statusCode == 1011:
            description = "Not found."
        elif statusCode == 1012:
            description = "General error."
        elif statusCode == 1013:
            description = "Dependencies need to be deleted"
        elif statusCode == 1014:
            description = "Unable to establish network connection."
        elif statusCode == 1015:
            description = "Your subscription date is greater than your server date."
        elif statusCode == 1016:
            description = "Incompatible database version."
        elif statusCode == 1100:
            description = "Unknown login error occurred."
        elif statusCode == 1109:
            description = "This integrated application registration key is already in use."
        elif statusCode == 1110:
            description = "A new integrated application has been added to Fishbowl. Please contact the Fishbowl administrator to approve this integrated application."
        elif statusCode == 1111:
            description = "This integrated application registration key does not match."
        elif statusCode == 1112:
            description = "This integrated application has not been approved by the Fishbowl administrator."
        elif statusCode == 1120:
            description = "Invalid username or password."
        elif statusCode == 1130:
            description = "Invalid ticket passed to Fishbowl server."
        elif statusCode == 1131:
            description = "Invalid ticket key passed to Fishbowl server."
        elif statusCode == 1140:
            description = "Initialization token is not correct type."
        elif statusCode == 1150:
            description = "Request was invalid."
        elif statusCode == 1161:
            description = "Response was invalid."
        elif statusCode == 1162:
            description = "The login limit has been reached for the server's key."
        elif statusCode == 1163:
            description = "Your API session has timed out."
        elif statusCode == 1164:
            description = "Your API session has been logged out."
        elif statusCode == 1200:
            description = "Custom field is invalid."
        elif statusCode == 1300:
            description = "Was not able to find the memo _________."
        elif statusCode == 1301:
            description = "The memo was invalid."
        elif statusCode == 1400:
            description = "Was not able to find the order history."
        elif statusCode == 1401:
            description = "The order history was invalid."
        elif statusCode == 1500:
            description = "The import was not properly formed."
        elif statusCode == 1501:
            description = "That import type is not supported."
        elif statusCode == 1502:
            description = "File not found."
        elif statusCode == 1503:
            description = "That export type is not supported."
        elif statusCode == 1504:
            description = "Unable to write to file."
        elif statusCode == 1505:
            description = "The import data was of the wrong type."
        elif statusCode == 1506:
            description = "Import requires a header."
        elif statusCode == 1600:
            description = "Unable to load the user."
        elif statusCode == 1601:
            description = "Unable to find the user."
        elif statusCode == 2000:
            description = "Was not able to find the part _________."
        elif statusCode == 2001:
            description = "The part was invalid."
        elif statusCode == 2002:
            description = "Was not able to find a unique part."
        elif statusCode == 2003:
            description = "BOM had an error on the part"
        elif statusCode == 2100:
            description = "Was not able to find the product _________."
        elif statusCode == 2101:
            description = "The product was invalid."
        elif statusCode == 2102:
            description = "The product is not unique"
        elif statusCode == 2120:
            description = "The kit item was invalid."
        elif statusCode == 2121:
            description = "The associated product was invalid."
        elif statusCode == 2200:
            description = "Yield failed."
        elif statusCode == 2201:
            description = "Commit failed."
        elif statusCode == 2202:
            description = "Add initial inventory failed."
        elif statusCode == 2203:
            description = "Cannot adjust committed inventory."
        elif statusCode == 2204:
            description = "Invalid quantity."
        elif statusCode == 2205:
            description = "Quantity must be greater than zero."
        elif statusCode == 2206:
            description = "Serial number _________ already committed."
        elif statusCode == 2207:
            description = "Part _________ is not an inventory part."
        elif statusCode == 2208:
            description = "Not enough available quantity in _________."
        elif statusCode == 2209:
            description = "Move failed."
        elif statusCode == 2210:
            description = "Cycle count failed."
        elif statusCode == 2300:
            description = "Was not able to find the tag number _________."
        elif statusCode == 2301:
            description = "The tag was invalid."
        elif statusCode == 2302:
            description = "The tag move failed."
        elif statusCode == 2303:
            description = "Was not able to save tag number _________."
        elif statusCode == 2304:
            description = "Not enough available inventory in tag number _________."
        elif statusCode == 2305:
            description = "Tag number _________ is a location."
        elif statusCode == 2400:
            description = "Invalid UOM."
        elif statusCode == 2401:
            description = "UOM _________ not found."
        elif statusCode == 2402:
            description = "Integer UOM _________ cannot have non-integer quantity."
        elif statusCode == 2403:
            description = "The UOM is not compatible with the part's base UOM."
        elif statusCode == 2404:
            description = "Cannot convert to the requested UOM"
        elif statusCode == 2405:
            description = "Cannot convert to the requested UOM"
        elif statusCode == 2406:
            description = "The quantity must be a whole number."
        elif statusCode == 2407:
            description = "The UOM conversion for the quantity must be a whole number."
        elif statusCode == 2500:
            description = "The tracking is not valid."
        elif statusCode == 2501:
            description = "Part tracking not found."
        elif statusCode == 2502:
            description = "The part tracking name is required."
        elif statusCode == 2503:
            description = "The part tracking name _________ is already in use."
        elif statusCode == 2504:
            description = "The part tracking abbreviation is required."
        elif statusCode == 2505:
            description = "The part tracking abbreviation _________ is already in use."
        elif statusCode == 2506:
            description = "The part tracking _________ is in use or was used and cannot be deleted."
        elif statusCode == 2510:
            description = "Serial number is missing."
        elif statusCode == 2511:
            description = "Serial number is null."
        elif statusCode == 2512:
            description = "Duplicate serial number."
        elif statusCode == 2513:
            description = "The serial number is not valid."
        elif statusCode == 2514:
            description = "Tracking is not equal."
        elif statusCode == 2515:
            description = "The tracking _________ was not found in location _________' or is committed to another order."
        elif statusCode == 2600:
            description = "Location _________ not found."
        elif statusCode == 2601:
            description = "Invalid location."
        elif statusCode == 2602:
            description = "Location group _________ not found."
        elif statusCode == 2603:
            description = "Default customer not specified for location _________."
        elif statusCode == 2604:
            description = "Default vendor not specified for location _________."
        elif statusCode == 2605:
            description = "Default location for part _________ not found."
        elif statusCode == 2606:
            description = "_________ is not a pickable location."
        elif statusCode == 2607:
            description = "_________ is not a receivable location."
        elif statusCode == 2700:
            description = "Location group not found."
        elif statusCode == 2701:
            description = "Invalid location group."
        elif statusCode == 2702:
            description = "User does not have access to location group _________."
        elif statusCode == 3000:
            description = "Customer _________ not found."
        elif statusCode == 3001:
            description = "Customer is invalid."
        elif statusCode == 3002:
            description = "Customer _________ must have a default main office address."
        elif statusCode == 3100:
            description = "Vendor _________ not found."
        elif statusCode == 3101:
            description = "Vendor is invalid."
        elif statusCode == 3300:
            description = "Address not found"
        elif statusCode == 3301:
            description = "Invalid address"
        elif statusCode == 4000:
            description = "There was an error loading PO _________."
        elif statusCode == 4001:
            description = "Unknown status _________."
        elif statusCode == 4002:
            description = "Unknown carrier _________."
        elif statusCode == 4003:
            description = "Unknown QuickBooks class _________."
        elif statusCode == 4004:
            description = "PO does not have a PO number. Please turn on the auto-assign PO number option in the purchase order module options."
        elif statusCode == 4005:
            description = "Duplicate order number _________."
        elif statusCode == 4006:
            description = "Cannot create PO with configurable parts: _________."
        elif statusCode == 4007:
            description = "The following parts were not added to the purchase order. They have no default vendor:"
        elif statusCode == 4008:
            description = "Unknown type _________."
        elif statusCode == 4100:
            description = "There was an error loading SO _________."
        elif statusCode == 4101:
            description = "Unknown salesman _________."
        elif statusCode == 4102:
            description = "Unknown tax rate _________."
        elif statusCode == 4103:
            description = "Cannot create SO with configurable parts: _________."
        elif statusCode == 4104:
            description = "The sales order item is invalid: _________."
        elif statusCode == 4105:
            description = "SO does not have a SO number. Please turn on the auto-assign SO numbers option in the sales order module options."
        elif statusCode == 4106:
            description = "Cannot create SO with kit products"
        elif statusCode == 4107:
            description = "A kit item must follow a kit header."
        elif statusCode == 4108:
            description = "Sales order cannot be found."
        elif statusCode == 4200:
            description = "There was an error loading BOM _________."
        elif statusCode == 4201:
            description = "Bill of materials cannot be found."
        elif statusCode == 4202:
            description = "Duplicate BOM number _________."
        elif statusCode == 4203:
            description = "The bill of materials is not up to date and must be reloaded."
        elif statusCode == 4204:
            description = "Bill of materials was not saved."
        elif statusCode == 4205:
            description = "Bill of materials is in use and cannot be deleted"
        elif statusCode == 4206:
            description = "requires a raw good and a finished good, or a repair."
        elif statusCode == 4207:
            description = "This change would make this a recursive bill of materials."
        elif statusCode == 4210:
            description = "There was an error loading MO _________."
        elif statusCode == 4211:
            description = "Manufacture order cannot be found."
        elif statusCode == 4212:
            description = "No manufacture order was created. Duplicate order number _________."
        elif statusCode == 4213:
            description = "The manufacture order is not up to date and must be reloaded."
        elif statusCode == 4214:
            description = "Manufacture order was not saved."
        elif statusCode == 4215:
            description = "Manufacture order is closed and cannot be modified."
        elif statusCode == 4220:
            description = "There was an error loading WO _________."
        elif statusCode == 4221:
            description = "Work order cannot be found."
        elif statusCode == 4222:
            description = "Duplicate work order number _________."
        elif statusCode == 4223:
            description = "The work order is not up to date and must be reloaded."
        elif statusCode == 4224:
            description = "Work order was not saved."
        elif statusCode == 4300:
            description = "There was an error loading TO _________."
        elif statusCode == 4301:
            description = "Unknown status _________."
        elif statusCode == 4302:
            description = "Unknown carrier _________."
        elif statusCode == 4303:
            description = "Transfer order cannot be found."
        elif statusCode == 4304:
            description = "TO does not have a TO number. Please turn on the auto-assign TO number option in the Transfer Order module options."
        elif statusCode == 4305:
            description = "Duplicate order number _________."
        elif statusCode == 4306:
            description = "Unknown type _________."
        elif statusCode == 4307:
            description = "Transfer order was not saved."
        elif statusCode == 4308:
            description = "The transfer order is not up to date and must be reloaded."
        elif statusCode == 5000:
            description = "There was a receiving error."
        elif statusCode == 5001:
            description = "Receive ticket invalid."
        elif statusCode == 5002:
            description = "Could not find a line item for part number _________."
        elif statusCode == 5003:
            description = "Could not find a line item for product number _________."
        elif statusCode == 5004:
            description = "Not a valid receive type."
        elif statusCode == 5005:
            description = "The receipt is not up to date and must be reloaded."
        elif statusCode == 5006:
            description = "A location is required to receive this part. Part num: _________"
        elif statusCode == 5007:
            description = "Cannot receive or reconcile more than the quantity ordered on a TO."
        elif statusCode == 5008:
            description = "Receipt not found _________."
        elif statusCode == 5100:
            description = "Pick invalid"
        elif statusCode == 5101:
            description = "Pick not found _________."
        elif statusCode == 5102:
            description = "Pick not saved."
        elif statusCode == 5103:
            description = "An order on pick _________ has a problem."
        elif statusCode == 5104:
            description = "Pick item not found _________."
        elif statusCode == 5105:
            description = "Could not finalize pick. Quantity is not correct."
        elif statusCode == 5106:
            description = "The pick is not up to date and must be reloaded."
        elif statusCode == 5107:
            description = "The part in tag _________ does not match part _________."
        elif statusCode == 5108:
            description = "Incorrect slot for this item. Item must be placed with others for this order."
        elif statusCode == 5109:
            description = "Wrong number of serial numbers sent for pick."
        elif statusCode == 5110:
            description = "Pick items must be started to assign tag."
        elif statusCode == 5111:
            description = "Order must be picked from location group _________."
        elif statusCode == 5112:
            description = "The item must be picked from _________."
        elif statusCode == 5200:
            description = "Shipment invalid"
        elif statusCode == 5201:
            description = "Shipment not found _________."
        elif statusCode == 5202:
            description = "Shipment status error"
        elif statusCode == 5203:
            description = "Unable to process shipment."
        elif statusCode == 5204:
            description = "Carrier not found _________."
        elif statusCode == 5205:
            description = "The shipment _________ has already been shipped."
        elif statusCode == 5206:
            description = "Cannot ship order _________. The customer has a ship hold."
        elif statusCode == 5207:
            description = "Cannot ship order _________. The vendor has a ship hold."
        elif statusCode == 5300:
            description = "Could not load RMA."
        elif statusCode == 5301:
            description = "Could not find RMA."
        elif statusCode == 5400:
            description = "Could not take payment."
        elif statusCode == 5500:
            description = "Could not load the calendar."
        elif statusCode == 5501:
            description = "Could not find the calendar."
        elif statusCode == 5502:
            description = "Could not save the calendar."
        elif statusCode == 5503:
            description = "Could not delete the calendar."
        elif statusCode == 5504:
            description = "Could not find the calendar activity."
        elif statusCode == 5505:
            description = "Could not save the calendar activity."
        elif statusCode == 5506:
            description = "Could not delete the calendar activity."
        elif statusCode == 5507:
            description = "The start date must be before the stop date."
        elif statusCode == 6000:
            description = "Account invalid"
        elif statusCode == 6001:
            description = "Discount invalid"
        elif statusCode == 6002:
            description = "Tax rate invalid"
        elif statusCode == 6003:
            description = "Accounting connection failed"
        elif statusCode == 6005:
            description = "Accounting system not defined"
        elif statusCode == 6006:
            description = "Accounting brought back a null result"
        elif statusCode == 6007:
            description = "Accounting synchronization error"
        elif statusCode == 6008:
            description = "The export failed"
        elif statusCode == 6009:
            description = "Fishbowl and Quickbooks multiple currency features don't match"
        elif statusCode == 6010:
            description = "The data validation for the export has failed."
        elif statusCode == 6011:
            description = "Accounting integration is not configured. Please reintegrate."
        elif statusCode == 6100:
            description = "Class already exists"
        elif statusCode == 7000:
            description = "Pricing rule error"
        elif statusCode == 7001:
            description = "Pricing rule not found"
        elif statusCode == 7002:
            description = "The pricing rule name is not unique"
        elif statusCode == 8000:
            description = "Unknown FOB _________."
        self.statusCode = statusCode
        self.statusDescription = description
