from threading import Thread
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import internalprocesses.corepricer.checkSales as checkSales
import internalprocesses.automation.automation as automation
from internalprocesses.fishbowlclient import FBConnection
from internalprocesses.masterinventory.mergeinventory import (
    uploadInventoryToFTP, emailInventorySheet
)
from internalprocesses import emailQuantitySoldReport

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
    orderImportThread = Thread(target=orderImportNewThread, args = (False, ))
    orderImportThread.start()
    return "Success"

@app.route("/import-orders-test")
def orderImportTest():
    orderImportThread = Thread(target=automation.orderImport)
    orderImportThread.start()
    return "Success"

@app.route("/upload-tracking")
def trackingUpload():
    trackingUploadThread = Thread(target=trackingUploadNewThread)
    trackingUploadThread.start()
    return "Success"

@app.route("/inventory-upload")
def inventoryUpload():
    inventoryUploadThread = Thread(target=inventoryUploadNewThread)
    inventoryUploadThread.start()
    return "Success"

@app.route("/email-inventory-file")
def emailInventoryFile():
    emailInventoryFileThread = Thread(target=emailInventorySheetNewThread)
    emailInventoryFileThread.start()
    return "Success"

@app.route("/yearly-sold-report")
def emailSoldReport():
    emailSoldReportThread = Thread(target=emailQuantitySoldReport)
    emailSoldReportThread.start()
    return "Success"

def trackingUploadNewThread():
    automation.trackingUpload()

def orderImportNewThread(test = True):
    automation.orderImport(test=test)

def inventoryUploadNewThread():
    uploadInventoryToFTP()

def emailInventorySheetNewThread():
    emailInventorySheet()

if __name__ == "__main__":
    app.run(debug = True)