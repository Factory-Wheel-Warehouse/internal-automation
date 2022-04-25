from gzip import READ
import io
import re
import os
from trace import CoverageResults
import traceback
import dotenv
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.fishbowlclient.fishbowl import FBConnection
from internalprocesses.wheelsourcing.wheelsourcing import COREPATTERN, buildVendorInventory

def _setVendorStock(vendorDetails):
    warehouse, coast, perfection = [0, 0], [0, 0], [0, 0]
    jante, roadReady, blackburns = [0, 0], [0, 0], [0, 0]
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
    if "Blackburns" in vendorDetails:
        blackburns = vendorDetails["Blackburns"]
    return warehouse + coast + perfection + jante + roadReady + blackburns

def _getCoreToFinishMap(ftpServer):
    coreToFinishMap = {}
    magentoSkus = ftpServer.getFileAsList(
        "/Factory_Wheel_Warehouse/combine_inventory/COMBINE_SHEET.csv"
    )
    for row in magentoSkus:
        sku = row[0]
        core = sku[:9]
        if sku[-1] != "N" or int(sku[9:11]) > 80:
            if core not in coreToFinishMap:
                coreToFinishMap[core] = [sku]
            else:
                coreToFinishMap[core].append(sku)
    return coreToFinishMap

def _convertCoresToFinished(ftpServer, coreInventory):
    output = {}
    coreToFinishMap = _getCoreToFinishMap(ftpServer)
    for core, vendorDetails in coreInventory.items():
        if core in coreToFinishMap:
            for finish in coreToFinishMap[core]:
                if finish not in output:
                    output[finish] = vendorDetails
                else:
                    for vendor, stock in vendorDetails.items():
                        if vendor in output[finish]:
                            output[finish][vendor][0] += stock[0]
                        else:
                            output[finish][vendor] = stock
    return output

def convertInventoryToList(ftpServer, fishbowl):
    combinedInventoryList = [
        [
            "Part Number", "Hollander", "U-Code", "Magento Quantity", "Core", 
            "Total Quantity", "Lowest Cost", "Highest Cost", "Warehouse",
            "Warehouse Cost", "Coast", "Coast Cost", "Perfection",
            "Perfection Cost", "Jante", "Jante Cost", "Road Ready", 
            "Road Ready Cost", "Blackburns", "Blackburns Cost"
        ]
    ]
    inventoryDict = buildVendorInventory(ftpServer, fishbowl)
    inventoryDict["Core"] = _convertCoresToFinished(
        ftpServer, inventoryDict["Core"]
    )
    total = 0
    for inventoryType, value in inventoryDict.items():
        core = False
        if inventoryType == "Core":
            core = True
        for partNum, value in value.items():
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
                    row = [
                        partNum, partNum[:8], partNum[8:], magentoQty, core, 
                        totalQty, minPrice, maxPrice
                        ] 
                    row += vendorStock
                    combinedInventoryList.append(row)
                    total += totalQty
            except:
                print(partNum, value)
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
