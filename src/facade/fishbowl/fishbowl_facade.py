import json
import os
import socket
import struct

from src.facade.fishbowl.fishbowl_status import status_codes


class FishbowlFacade:
    USERNAME: str = "danny"
    PASSWORD: str = os.getenv("FISHBOWL-PW")
    HOST: str = "factorywheelwarehouse.myfishbowl.com"
    PORT: int = 28192

    def __init__(self):
        self.key = ""
        self.stream = None
        self.general_status = None
        self.request_specific_status = None

    def start(self):
        self.connect()
        self.loginRequest()

    def connect(self):

        """Initializes a socket and connects to the HOST and port."""
        self.stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.stream.settimeout(300)
        self.stream.connect((self.HOST, self.PORT))

    def close(self):

        """
        Closes the fishbowl connection by sending a logout request to the
        Fishbowl API and the closing the socket.
        """
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

    def setStatus(self, response):
        response_message = response["FbiJson"]["FbiMsgsRs"]
        self.general_status = response_message["statusCode"]
        if self.general_status not in [900, 1000, 1164]:
            raise Exception(f"Fishbowl request generic error:\n"
                            f"{self.general_status} - "
                            f"{status_codes[self.general_status]}")
        for key, value in response_message.items():
            if key != 'statusCode' and 'Rs' in key:
                self.request_specific_status = value["statusCode"]
                if self.request_specific_status not in [900, 1000]:
                    try:
                        description = value["statusMessage"]
                    except KeyError:
                        description = "Description not provided"
                    raise Exception(f"Fishbowl request specific error:"
                                    f"\n{self.request_specific_status} - "
                                    f"{description}")

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
        self.setStatus(responseJson)
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
                        "UserName": self.USERNAME,
                        "UserPassword": self.PASSWORD
                    }
                }
            }
        }
        response = self.sendRequest(jsonDict)
        if self.general_status == 1000:
            self.key = response["FbiJson"]["Ticket"]["Key"]
        else:
            status = {
                "general_code": str(self.general_status),
                "general_description": status_codes.get(self.general_status),
                "code": str(self.request_specific_status),
                "description": status_codes.get(self.request_specific_status)
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
            '"PartNumber", "PartDescription", "UOM", "PartType", '
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
            f'"{partNumber}", "{partNumber}", "Coast to Coast", '
            f'"true", "{partNumber}", 0'
        )
        response = self.sendImportRequest(
            data, "ImportPartProductAndVendorPricing"
        )
        return response

    def adjust_vendor_part_cost(self, partNumber, vendor_name, cost):

        """Adjusts the cost for a part number from a specified vendor"""

        data = [
            '"PartNumber", "ProductNumber", "Vendor", "DefaultVendor", ' \
            '"VendorPartNumber", "Cost"'
        ]
        data.append(
            f'"{partNumber}", "{partNumber}", "{vendor_name}", {True}, '
            f'"{partNumber}", {cost}'
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
            '"Flag", "SONum", "Status", "CustomerName", "CustomerContact", '
            '"BillToName", "BillToAddress", "BillToCity", "BillToState", '
            '"BillToZip", "BillToCountry", "ShipToName", "ShipToAddress", '
            '"ShipToCity", "ShipToState", "ShipToZip", "ShipToCountry", '
            '"ShipToResidential", "CarrierName", "TaxRateName", '
            '"PriorityId", "PONum"',
            '"Flag", "SOItemTypeID", "ProductNumber", "ProductDescription", '
            '"ProductQuantity", "UOM", "ProductPrice", "Taxable", "TaxCode", '
            '"Note", "ItemQuickBooksClassName", "ItemDateScheduled", '
            '"ShowItem", "KitItem", "RevisionLevel", "CustomerPartNumber"'
        ]
        data += soData
        response = self.sendImportRequest(data, "ImportSalesOrder")
        return response

    def importPurchaseOrder(self, poData):

        """Adds a purchase order into Fishbowl."""

        data = [
            'Flag, PONum, Status, VendorName, VendorContact, RemitToName, '
            'RemitToAddress, RemitToCity, RemitToState, RemitToZip, '
            'RemitToCountry, ShipToName, DeliverToName, ShipToAddress, '
            'ShipToCity, ShipToState, ShipToZip, ShipToCountry, CarrierName',
            'Flag, POItemTypeID, PartNumber, VendorPartNumber, PartQuantity, '
            'UOM, PartPrice'
        ]
        data += poData
        response = self.sendImportRequest(data, "ImportPurchaseOrder")
        return response

    def get_po_fulfillment_details(self, po_num: str):
        query = f"""
        SELECT b.vendorPartNum, b.qtyToFulfill, b.unitCost
        FROM po a
        LEFT JOIN poitem b
        ON a.id = b.poId
        WHERE a.num = "{po_num}";
        """
        response = self.sendQueryRequest(query)
        results = response["FbiJson"]["FbiMsgsRs"]["ExecuteQueryRs"]["Rows"][
            "Row"]
        return results

    def fulfill_po(self, po_num: str):
        data = ["PONum, Fulfill, VendorPartNum, Qty"]
        fulfillment_details = self.get_po_fulfillment_details(po_num)
        try:
            for row in fulfillment_details[1:]:
                row_data = [el.strip("\"") for el in row.split(',')]
                vendor_part_num, qty = row_data[0], int(float(row_data[1]))
                cost = float(row_data[2])
                if cost > 0:
                    data.append(f"{po_num}, {True}, {vendor_part_num}, {qty}")
                    return self.sendImportRequest(data, "ImportReceivingData")
        except IndexError as e:
            print(e)
            return None

    def _parse_query_request_response(self, response: dict):
        query_response = response["FbiJson"]["FbiMsgsRs"]["ExecuteQueryRs"]
        data = query_response["Rows"]["Row"]
        if isinstance(data, list):
            return [[el.strip("\"") for el in row.split(",")] for row in data]
        else:
            return [[el.strip("\"") for el in data.split(",")]]

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
        if not soNum:
            return
        query = f"""
        SELECT id 
        FROM ship 
        WHERE ship.num = "S{soNum}"
        """
        response = self.sendQueryRequest(query)
        shipID = response["FbiJson"]["FbiMsgsRs"]["ExecuteQueryRs"] \
            ["Rows"]["Row"][1].strip('"')
        if not shipID or shipID == "i":
            return
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
        """
        Inventory ranges taken from fishbowl "location" table
        """
        query = """
        SELECT STOCK.num, STOCK.qty, PARTCOST.avgCost
        FROM (
            SELECT PART.id as id, PART.num as num, QOHVIEW.qty as qty
            FROM QOHVIEW
            LEFT JOIN PART
            ON QOHVIEW.partid = PART.id
            WHERE QOHVIEW.qty > 0
            AND (
                QOHVIEW.LOCATIONID BETWEEN 612 AND 1053
                OR QOHVIEW.LOCATIONID BETWEEN 1062 AND 1477
            )
        ) as STOCK
        LEFT JOIN PARTCOST
        ON STOCK.id = PARTCOST.id
        WHERE num LIKE "ALY%"
            OR num LIKE "STL%"
            OR num LIKE "FWC%";
        """
        response = self.sendQueryRequest(query)
        return response["FbiJson"]["FbiMsgsRs"]["ExecuteQueryRs"] \
            ["Rows"]["Row"]
