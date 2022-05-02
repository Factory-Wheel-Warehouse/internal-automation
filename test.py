import os
import csv
import traceback
from dotenv import load_dotenv
from internalprocesses.automation.automation import InternalAutomation, orderImport
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
    inventory = buildVendorInventory(ftpServer, fishbowl)
    print(f"Available finished ALY75161U20: {inventory['Finished'].get('ALY75161U20')}")
    print(f"Available core ALY75161U20: {inventory['Core'].get('ALY75161U')}")
    print(assignCheapestVendor("ALY64098U45", 4, inventory))
    masterInventoryList = convertInventoryToList(ftpServer, fishbowl)
    path = "Factory_Wheel_Warehouse/MergedVendorInventory.csv"
    with open("testOutput.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(masterInventoryList)
    print(orderImport(test=True))
except:
    print(traceback.print_exc())
finally:
    fishbowl.close()
    ftpServer.close()
    pass