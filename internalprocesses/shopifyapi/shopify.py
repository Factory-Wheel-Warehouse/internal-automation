import requests

class ShopifyConnection():
    
    def __init__(self, shopifyConfig, password, apiKey):

        """Initializes the base http request url and loads the config"""
        self.config = shopifyConfig
        self._password = password
        self._apiKey = apiKey
        self.baseRequest = self.formatEndpoint()

    def formatEndpoint(self):

        """Returns a formatted url for future requests"""

        hostname = self.config["hostname"]
        version = self.config["version"]
        return f"https://{self._apiKey}:{self._password}@{hostname}/admin/api/{version}/"

    def getPendingOrders(self):

        """Returns a list of open and paid but unshipped orders"""

        params = {
            "fulfillment_status" : "unfillfilled",
            "financial_status" : "paid",
            "fields" : "id"
        }
        response = requests.get(
            self.baseRequest + "orders.json",
            params = params
        )
        return [order["id"] for order in response.json()["orders"]]

    def getOrderDetails(self, orderID):

        """Return order details of a given order"""

        fields = ["note_attributes", "line_items", "shipping_address"]
        params = {
            "fields" : ",".join(fields)
        }
        response = requests.get(
            self.baseRequest + f"orders/{orderID}.json",
            params = params
        )
        return response.json()["order"]
