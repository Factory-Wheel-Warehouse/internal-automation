import io
import os
import traceback
import dotenv
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.fishbowlclient.fishbowl import FBConnection
from internalprocesses.wheelsourcing.wheelsourcing import *
from internalprocesses.magentoapi.magento import MagentoConnection

def _setVendorStock(vendorDetails):
    warehouse, coast, perfection = [0, 0], [0, 0], [0, 0]
    jante, roadReady = [0, 0], [0, 0]
    if "Warehouse" in vendorDetails:
        warehouse = vendorDetails["Warehouse"]
    if "Perfection" in vendorDetails:
        perfection = vendorDetails["Perfection"]
    if "Coast" in vendorDetails:
        coast = vendorDetails["Coast"]
    if "Jante" in vendorDetails:
        jante = vendorDetails["Jante"]
    if "Road Ready" in vendorDetails:
        roadReady = vendorDetails["Road Ready"]
    return warehouse + coast + perfection + jante + roadReady

def convertInventoryToList(ftpServer, fishbowl):
    combinedInventoryList = [
        [
            "Part Number","Magento Quantity", "Total Quantity", "Lowest Cost", 
            "Highest Cost", "Warehouse", "Warehouse Cost", "Coast", 
            "Coast Cost", "Perfection", "Perfection Cost", "Jante", 
            "Jante Cost", "Road Ready", "Road Ready Cost"
        ]
    ]
    inventoryDict = buildVendorInventory(ftpServer, fishbowl)
    total = 0
    for partNum, value in inventoryDict.items():
        try:
            totalQty = sum(
                [vendorDetails[0] for vendorDetails in value.values()]
            )
            magentoQty = totalQty if totalQty < 5 else 5
            minPrice = min(
                [vendorDetails[1] for vendorDetails in value.values()]
            )
            maxPrice = max(
                [vendorDetails[1] for vendorDetails in value.values()]
            )
            vendorStock = _setVendorStock(value)
            if totalQty:
                row = [partNum, magentoQty, totalQty, minPrice, maxPrice] 
                row += vendorStock
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
