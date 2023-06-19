from threading import Thread
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import internalprocesses.corepricer.checkSales as checkSales
from internalprocesses.automation import *
from internalprocesses.masterinventory.mergeinventory import (
    uploadInventoryToFTP, emailInventorySheet
)
from internalprocesses import email_quantity_sold_report

app = Flask(__name__)
priceList = checkSales.buildPriceDict()  # 3268 entries


@app.route("/")
def index():
    return "<h1>Service is live<h1>"


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
    orderImportThread = Thread(target=orderImportNewThread, args=(False,))
    orderImportThread.start()
    return "Success"


@app.route("/import-orders-test")
def orderImportTest():
    orderImportThread = Thread(target=order_import)
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
    emailSoldReportThread = Thread(target=email_quantity_sold_report)
    emailSoldReportThread.start()
    return "Success"


@app.route("/upload_inventory_source_data")
def upload_inventory_source_data():
    thread = Thread(target=update_inventory_source_data)
    thread.start()
    return "Success"


@app.route("/warehouse-inventory-upload")
def warehouse_inventory_upload_endpoint():
    Thread(target=warehouse_inventory_upload).start()
    return "Success"


@app.route("/email_ship_by_notifications")
def update_inventory_source_data():
    Thread(target=email_ship_by_notifications).start()
    return "Success"


def trackingUploadNewThread():
    tracking_upload()


def orderImportNewThread(test=True):
    order_import(test=test)


def inventoryUploadNewThread():
    uploadInventoryToFTP()


def emailInventorySheetNewThread():
    emailInventorySheet()


if __name__ == "__main__":
    app.run(debug=True)
