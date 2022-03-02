from zeep import Client

wsdl = "https://lkqintegrationqc.ekeyconnect.com/Ordering.svc?wsdl"

client = Client(wsdl=wsdl)
checkDropShipAvailability = {
    "request": {
        "UserRequestInfo": {
            "AccountNumber": "837903",
            "BusinessTypeForAccountNumber": "Salvage",
            "UserName": "837903.factorywheel",
            "UserPassword": "fact0rywh33l",
            "VerificationCode": "3ecb234b-b7c7-40aa-926e-85ac0a82f5bb"
        },
        "PartsWithQuantity": [
            {
                "PartWithQuantityRequest": {
                    "PartNumber": "ALY64108U45",
                    "Quantity": 1
                }
            }
        ]
    }
}
# can pass in dictionaries to methods
print(client.service.CheckDropShipAvailability(**checkDropShipAvailability))
