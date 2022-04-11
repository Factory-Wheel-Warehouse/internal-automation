from doctest import master
import os
import csv
import traceback
from dotenv import load_dotenv
from internalprocesses.automation.automation import InternalAutomation
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.fishbowlclient.fishbowl import FBConnection
from internalprocesses.wheelsourcing.wheelsourcing import *
from internalprocesses.masterinventory.mergeinventory import convertInventoryToList

load_dotenv()

ftpPassword = os.getenv("FTP-PW")
fbPassword = os.getenv("FISHBOWL-PW")

ftpServer = FTPConnection("54.211.94.170", 21, "danny", ftpPassword)
fishbowl = FBConnection("danny", fbPassword, "factorywheelwarehouse.myfishbowl.com")
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