import io
import json
import os
import traceback
from base64 import b64encode
from dotenv import load_dotenv
from internalprocesses.fishbowlclient.fishbowl import FBConnection
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.outlookapi.outlook import OutlookConnection
from internalprocesses.wheelsourcing.wheelsourcing import (
    COREPATTERN, buildVendorInventory)


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

def _coastCorePricing(ftpServer):
    priceList = ftpServer.getFileAsList(
        "/lkq/Factory Wheel Warehouse_837903.csv"
    )
    priceDict = {}
    for row in priceList:
        priceDict[row[2]] = row[26]
    return priceDict

def _convertCoresToFinished(ftpServer, coreInventory):
    output = {}
    coastPriceDict = _coastCorePricing(ftpServer)
    coreToFinishMap = _getCoreToFinishMap(ftpServer)
    for core, vendorDetails in coreInventory.items():
        if core in coreToFinishMap:
            for finish in coreToFinishMap[core]:
                finishedCost = coastPriceDict.get(finish)
                coastDetails = vendorDetails.get("Coast")
                if coastDetails:
                    cost = int(vendorDetails["Coast"][1])
                    if finishedCost:
                        finishedCost = int(finishedCost)
                        if cost < finishedCost:
                            type_ = finish[:3]
                            finishedCost += 12.5 if type_ == "ALY" else 17.5
                            vendorDetails["Coast"][1] = finishedCost
                    else:
                        if cost <= 0:
                            vendorDetails["Coast"][1] = -1
                if finish not in output:
                    output[finish] = vendorDetails
                else:
                    for vendor, stock in vendorDetails.items():
                        if vendor in output[finish]:
                            output[finish][vendor][0] += stock[0]
                        else:
                            output[finish][vendor] = stock
    return output

def _getFishbowlProductPriceDict(fishbowl):
    priceDict = {}
    data = fishbowl.sendQueryRequest(
        "SELECT num as SKU, price as Price FROM PRODUCT"
    )["FbiJson"]["FbiMsgsRs"]["ExecuteQueryRs"]["Rows"]["Row"]
    for row in data[1:]:
        strippedRow = [value.strip('"') for value in row.split(",")]
        sku = strippedRow[0]
        price = strippedRow[1]
        if sku and price:
            price = round(float(price), 2)
            priceDict[sku] = price
        else:
            print(f"Exception: {row}")
    return priceDict

def convertInventoryToList(ftpServer, fishbowl):
    combinedInventoryList = [
        [
            "Part Number", "Price", "Hollander", "U-Code", "Magento Quantity", 
            "Core", "Total Quantity", "Lowest Cost", "Highest Cost",
            "Warehouse", "Warehouse Cost", "Coast", "Coast Cost", "Perfection",
            "Perfection Cost", "Jante", "Jante Cost", "Road Ready", 
            "Road Ready Cost", "Blackburns", "Blackburns Cost"
        ]
    ]
    inventoryDict = buildVendorInventory(ftpServer, fishbowl)
    inventoryDict["Core"] = _convertCoresToFinished(
        ftpServer, inventoryDict["Core"]
    )
    total = 0
    fishbowlPriceDict = _getFishbowlProductPriceDict(fishbowl)
    for inventoryType, value in inventoryDict.items():
        core = False
        if inventoryType == "Core":
            core = True
        for partNum, value in value.items():
            try:
                price = fishbowlPriceDict.get(partNum)
                if price == None:
                    price = -1
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
                        partNum, price, partNum[:8], partNum[8:], magentoQty, 
                        core, totalQty, minPrice, maxPrice
                        ] 
                    row += vendorStock
                    combinedInventoryList.append(row)
                    total += totalQty
            except:
                print(partNum, value)
                raise Exception()
    return combinedInventoryList

def uploadInventoryToFTP():
    load_dotenv()
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

def emailInventorySheet():
    try:
        load_dotenv()
        ftpPassword = os.getenv("FTP-PW")
        outlookPassword = os.getenv("OUTLOOK-PW")
        outlookCS = os.getenv("OUTLOOK-CS")
        with open(
            os.path.join(
                os.path.dirname(__file__), "..", "..", "data/config.json"
            )
        ) as configFile:
            outlookConfig = json.load(configFile)["APIConfig"]["Outlook"]["Danny"]
        outlook = OutlookConnection(outlookConfig, outlookPassword, outlookCS)
        ftpServer = FTPConnection("54.211.94.170", 21, "danny", ftpPassword)
        inventoryFileBinary = ftpServer.getFileAsBinary(
            "Factory_Wheel_Warehouse/MergedVendorInventory.csv"
        ).read()
        inventoryFileEDMBinary = b64encode(inventoryFileBinary).decode()
        subject = "Merged Inventory Sheet"
        body = "The merged vendor inventory sheet is attached to this email."
        outlook.sendMail(
            "sales@factorywheelwarehouse.com", subject, body,
            attachment = inventoryFileEDMBinary, 
            attachmentName = "MergedVendorInventory.csv"
        )
    except:
        print(traceback.print_exc())
    finally:
        ftpServer.close()
