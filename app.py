from threading import Thread
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import internalprocesses.corepricer.checkSales as checkSales
import internalprocesses.automation.automation as automation
from internalprocesses.masterinventory.mergeinventory import uploadInventoryToFTP

app = Flask(__name__)
priceList = checkSales.buildPriceDict() #3268 entries

@app.route("/")
def index():
    return "<h1>Service is live bitches!!!<h1>"

@app.route("/sms", methods=["GET", "POST"])
def reply():
    query = request.values.get('Body', None)
    resp = MessagingResponse()
    if str(query).strip().lower() == "test":
        resp.message("Aced!")
        return str(resp)
    hollanders = query.strip().split(", ")
    body = ""
    for hollander in hollanders:
        while len(hollander) < 5:
            hollander = "0" + hollander
        body += checkSales.checkHollander(hollander, priceList)
    resp.message(body)
    return str(resp)

@app.route("/import-orders")
def orderImport():
    orderImport = Thread(target=orderImportNewThread, args = (False, ))
    orderImport.start()
    return "Success"

@app.route("/import-orders-test")
def orderImportTest():
    orderImport = Thread(target=orderImportNewThread)
    orderImport.start()
    return "Success"

@app.route("/upload-tracking")
def trackingUpload():
    trackingUpload = Thread(target=trackingUploadNewThread)
    trackingUpload.start()
    return "Success"

@app.route("/inventory-upload")
def inventoryUpload():
    inventoryUpload = Thread(target=inventoryUploadNewThread)
    inventoryUpload.start()
    return "Success"

def trackingUploadNewThread():
    automation.trackingUpload()

def orderImportNewThread(test = True):
    automation.orderImport(test = test)

def inventoryUploadNewThread():
    uploadInventoryToFTP()

if __name__ == "__main__":
    app.run()