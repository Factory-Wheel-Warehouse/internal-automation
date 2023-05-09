import re
import requests
from datetime import date, timedelta


class MagentoConnection():

    def __init__(self, accessToken):
        self.baseRequest = "https://factorywheelwarehouse.com/rest/default/V1/"
        self._accessToken = accessToken
        self.headers = {
            "Authorization": f"Bearer {self._accessToken}"
        }

    def buildSearchCriteria(
            self, params, field, value, condition_type, group=0
    ):
        base = f"searchCriteria[filter_groups][{group}][filters][0]"
        params[base + "[field]"] = field
        params[base + "[value]"] = value
        params[base + "[condition_type]"] = condition_type

    def getPendingOrders(self):

        """ eBay orders are the US100000#### orders """
        """ Amazon ###-#######-####### where x in range(0-10) """
        """ Walmart [0-9]{13} """
        """ Website 100000#### """

        params = {}
        self.buildSearchCriteria(
            params=params, field="status",
            value="processing, unshipped", condition_type="in"
        )
        self.buildSearchCriteria(
            params=params, field="created_at",
            value=str(date.today() - timedelta(days=21)),
            condition_type="gt", group=1
        )
        response = requests.get(
            self.baseRequest + "orders/",
            headers=self.headers,
            params=params
        )
        return [order["increment_id"] for order in response.json()["items"]]

    def getOrder(self, incrementID):
        params = {}
        self.buildSearchCriteria(
            params=params, field="increment_id",
            value=incrementID,
            condition_type="eq", group=1
        )
        response = requests.get(
            self.baseRequest + f"orders/",
            headers=self.headers,
            params=params
        )
        return response.json()

    def getOrderDetails(self, incrementID):
        order = self.getOrder(incrementID)
        return order["items"][0]

    def isAmazonOrder(self, incrementID):
        return bool(re.match(r"^[0-9]{3}-[0-9]{7}-[0-9]{7}$", incrementID))

    def isEbayOrder(self, incrementID):
        return bool(
            re.match(r"^[A-Z]{1}[0-9]{2}-[0-9]{5}-[0-9]{5}$", incrementID) or
            re.match(r"^[0-9]{2}-[0-9]{5}-[0-9]{5}$", incrementID)
        )

    def getEbayAccount(self, incrementID):
        if self.isEbayOrder(incrementID) and incrementID[0] == "A":
            return "Main Ebay"
        elif self.isEbayOrder(incrementID) and incrementID[0] == "B":
            return "Ebay Albany"
        elif self.isEbayOrder(incrementID) and incrementID[0] == "C":
            return "OED"

    def isWalmartOrder(self, incrementID):
        return bool(re.match(r"^[0-9]{15}$", incrementID))

    def isWebsiteOrder(self, incrementID):
        return bool(re.match(r"^[0-9]{10}$", incrementID))

    def getCarrier(self, trackingNumber):
        if re.findall(r"^1Z[a-z|A-Z|0-9]{8}[0-9]{8}$", trackingNumber):
            return "ups"
        elif re.findall(r"^[0-9]{12}$", trackingNumber):
            return "fedex"

    def trackingNumberCarrier(self, trackingNumber):
        carrier, title = None, None
        if self.getCarrier(trackingNumber) == "ups":
            carrier, title = "ups", "United Parcel Service"
        elif self.getCarrier(trackingNumber) == "fedex":
            carrier, title = "fedex", "Federal Express"
        return [carrier, title]

    def buildShipmentUploadPayload(self, carrier, title, trackingNumber,
                                   order):
        payload = {
            "items": [],
            "notify": self.isWebsiteOrder(order["increment_id"]),
            "tracks": []
        }
        if carrier:
            addTracking = False
            for i in range(len(order["items"])):
                qtyOrdered = order["items"][i]["qty_ordered"]
                qtyShipped = order["items"][i]["qty_shipped"]
                if qtyOrdered - qtyShipped > 0:
                    addTracking = True
                    payload["items"].append(
                        {
                            "order_item_id": order["items"][i]["item_id"],
                            "qty": qtyOrdered - qtyShipped
                        }
                    )
            if addTracking:
                payload["tracks"].append(
                    {
                        "track_number": trackingNumber,
                        "title": title,
                        "carrier_code": self.getCarrier(trackingNumber)
                    }
                )
                return payload

    def addOrderTracking(self, incrementID, trackingNumber):
        """
        https://magento.redoc.ly/2.4.3-admin/tag/orderincrementIDship
        endpoint -> order/{orderID}/ship
        """
        order = self.getOrderDetails(incrementID)
        orderID = order["items"][0]["order_id"]
        carrier, title = self.trackingNumberCarrier(trackingNumber)
        payload = self.buildShipmentUploadPayload(carrier, title,
                                                  trackingNumber, order)
        if payload and payload["items"] and payload['tracks']:
            return requests.post(
                url=self.baseRequest + f"order/{orderID}/ship",
                headers=self.headers,
                json=payload
            )

    def productSearch(self, partNum):
        params = {}
        self.buildSearchCriteria(
            params=params, field="sku",
            value=f"{partNum}__", condition_type="like"
        )
        return requests.get(
            self.baseRequest + f"products",
            headers=self.headers,
            params=params
        ).json()
