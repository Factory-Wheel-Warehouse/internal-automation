import json
import requests

class TrackingChecker():

    def __init__(self):
        self._headers = {
            "Content-Type" : "application/json",
            "Tracktry-Api-Key" : "d9fec218-7fe4-401a-8590-c5d0cd2e47e6"
        }
        self._baseURL = "https://api.tracktry.com/v1/trackings"
        self._statusCode = 0

    @property
    def statusCode(self): return self._statusCode

    @statusCode.setter
    def statusCode(self, statusCode): self._statusCode = statusCode

    def _request(method="GET"):
        def inner(func):
            def wrapper(self, *args, **kwargs):
                relativeURL, json = func(*args, **kwargs)
                url = self._baseURL + relativeURL
                response = requests.request(
                    method=method, url=url, 
                    headers=self._headers, json=json
                ).json()
                self.statusCode = response["meta"]["code"]
                return response
            return wrapper
        return inner
    
    @_request("POST")
    def addSingleTracking(trackingNumber, carrier, orderID):
        relativeURL = '/post'
        json = {
            "tracking_number" : trackingNumber,
            "carrier_code" : carrier,
            "order_id" : orderID
        }
        return relativeURL, json
    
    @_request("POST")
    def batchAddTracking(trackingNumbers):
        relativeURL = '/batch'
        json = []
        if len(trackingNumbers) < 41:
            for i in range(len(trackingNumbers)):
                json.append(
                    {
                        "tracking_number" : trackingNumbers[0],
                        "carrier_code" : trackingNumbers[1],
                        "orderID" : trackingNumbers[2]
                    }
                )
            return relativeURL, json

    @_request()
    def checkTracking(trackingNumber, carrier):
        relativeURL = f'/{carrier}/{trackingNumber}'
        return relativeURL, None
    
    @_request("DELETE")
    def deleteTracking(trackingNumber, carrier):
        relativeURL = f'{carrier}/{trackingNumber}'
        return relativeURL, None

if __name__ == "__main__":
    trackingChecker = TrackingChecker()
    print(trackingChecker.checkTracking("1ZRW16610307465798", "ups"))
    print(trackingChecker.statusCode)