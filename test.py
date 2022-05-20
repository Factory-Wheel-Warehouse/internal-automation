from ast import Bytes
import email
import os
import csv
import pickle
import traceback
from dotenv import load_dotenv
from internalprocesses.automation.automation import InternalAutomation, orderImport
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.fishbowlclient.fishbowl import FBConnection
from internalprocesses.outlookapi.outlook import OutlookConnection
from internalprocesses.wheelsourcing.wheelsourcing import *
from internalprocesses.masterinventory.mergeinventory import convertInventoryToList
from io import BytesIO
from internalprocesses.masterinventory.mergeinventory import emailInventorySheet

load_dotenv()


ftpPassword = os.getenv("FTP-PW")
fbPassword = os.getenv("FISHBOWL-PW")
outlookPassword = os.getenv("OUTLOOK-PW")
secret = os.getenv("OUTLOOK-CS")

ftpServer = FTPConnection("54.211.94.170", 21, "danny", ftpPassword)
fishbowl = FBConnection("danny", fbPassword, "factorywheelwarehouse.myfishbowl.com")
# outlook = OutlookConnection(outlookConfig, outlookPassword, secret)

try:
    masterInventoryList = convertInventoryToList(ftpServer, fishbowl)
    path = "Factory_Wheel_Warehouse/MergedVendorInventory.csv"
    with open("testOutput.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(masterInventoryList)
except:
    print(traceback.print_exc())
finally:
    fishbowl.close()
    ftpServer.close()
    print("Complete")
    pass