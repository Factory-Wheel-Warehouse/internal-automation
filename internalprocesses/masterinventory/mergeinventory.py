import io
import os
import traceback
import dotenv
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.fishbowlclient.fishbowl import FBConnection
from internalprocesses.wheelsourcing.wheelsourcing import *
from internalprocesses.magentoapi.magento import MagentoConnection

def _setVendorStock(vendorDetails):
    warehouse, coast, perfection, jante, roadReady = 0, 0, 0, 0, 0
    if "Warehouse" in vendorDetails:
        warehouse += vendorDetails["Warehouse"][0]
    if "Perfection" in vendorDetails:
        perfection += vendorDetails["Perfection"][0]
    if "Coast" in vendorDetails:
        coast += vendorDetails["Coast"][0]
    if "Jante" in vendorDetails:
        jante += vendorDetails["Jante"][0]
    if "Road Ready" in vendorDetails:
        roadReady += vendorDetails["Road Ready"][0]
    return [warehouse, coast, perfection, jante, roadReady]

def convertInventoryToList(ftpServer, fishbowl):
    combinedInventoryList = [["Part Number", "Total Quantity", "Lowest Cost", "Highest Cost", "Warehouse", "Coast", "Perfection", "Jante", "Road Ready"]]
    inventoryDict = buildVendorInventory(ftpServer, fishbowl)
    total = 0
    for partNum, value in inventoryDict.items():
        try:
            totalQty = sum(
                [vendorDetails[0] for vendorDetails in value.values()]
            )
            minPrice = min([vendorDetails[1] for vendorDetails in value.values()])
            maxPrice = max([vendorDetails[1] for vendorDetails in value.values()])
            vendorStock = _setVendorStock(value)
            if totalQty:
                row = [partNum, totalQty, minPrice, maxPrice] + vendorStock
                combinedInventoryList.append(row)
                total += totalQty
        except TypeError:
            print(f"Incompatible data types for {partNum}: {traceback.print_exc()}")
    return combinedInventoryList

def uploadInventoryToFTP():
    dotenv.load_dotenv()
    ftpPassword = os.getenv("FTP-PW")
    fbPassword = os.getenv("FISHBOWL-PW")
    ftpServer = FTPConnection("54.211.94.170", 21, "danny", ftpPassword)
    fishbowl = FBConnection(
        "danny", fbPassword, "factorywheelwarehouse.myfishbowl.com"
    )
    try:
        masterInventoryList = convertInventoryToList(ftpServer, fishbowl)
        path = "Factory_Wheel_Warehouse/MergedVendorInventory.csv"
        ftpServer.writeListAsCSV(path, masterInventoryList)
    except:
        print(traceback.print_exc())
    finally:
        fishbowl.close()
