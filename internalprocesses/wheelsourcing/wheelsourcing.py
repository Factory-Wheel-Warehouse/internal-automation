import re
import csv
from math import inf

FINISHPATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}[0-9]{2}$"
REPLICAPATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}[0-9]{2}N{1}$"
COREPATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}$"
ROADREADYREPLICAPATTERN = r"(ALY|STL|FWC)0[0-9]{5}[A-Z]{1}[0-9]{2}N{1}$"
FWWCOREPATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}[0-9]{2}\*CORE$"

CORE_MIN_QTY = 5
FINISHED_MIN_QTY = 3

def _formatWarehouseSKU(partNum):
    partNum = partNum.upper()
    if re.match(FINISHPATTERN, partNum):
        return partNum
    if re.match(REPLICAPATTERN, partNum):
        return partNum
    if re.match(FWWCOREPATTERN, partNum):
        return partNum[:9]

def _addToInventory(inventoryDictionary, partNum, vendor, qty, cost):
    if partNum not in inventoryDictionary:
        inventoryDictionary[partNum] = {vendor: [qty, cost]}
    else:
        if vendor not in inventoryDictionary[partNum]:
            inventoryDictionary[partNum][vendor] = [qty, cost]
        else:
            inventoryDictionary[partNum][vendor][0] += qty

def _addWarehouseInventory(fishbowl, coreInventory, finishedInventory):
    warehouseInventory = fishbowl.getPartsOnHand()
    for row in warehouseInventory[1:]:
        rawPartNum, qty, avgCost = [
            element.strip('"') for element in row.split(",")
        ]
        partNum = _formatWarehouseSKU(rawPartNum)
        qty = int(float(qty))
        if avgCost:
            avgCost = round(float(avgCost), ndigits=2)
        else:
            avgCost = 0.0
        if partNum and qty:
            if re.match(COREPATTERN, partNum):
                _addToInventory(
                    coreInventory, partNum, "Warehouse", qty, avgCost
                )
            else:
                _addToInventory(
                    finishedInventory, partNum, "Warehouse", qty, avgCost
                )

def _addPartAndCost(
    partColumn, costColumn, qtyColumn, vendorInventory,
    vendorName, coreInventory, finishedInventory
):
    for row in vendorInventory:
        partNum = row[partColumn]
        cost, qty = float(row[costColumn]), int(row[qtyColumn])
        if vendorName == "Coast":
            if str(partNum)[:3] == "ALY":
                cost += 12.50
            elif str(partNum)[:3] == "STL":
                cost += 17.50
        if re.match(ROADREADYREPLICAPATTERN, partNum):
            partNum = partNum[:3] + partNum[4:]
        if (
            re.match(FINISHPATTERN, partNum) or 
            re.match(REPLICAPATTERN, partNum)
        ):  
            if qty >= FINISHED_MIN_QTY:
                _addToInventory(
                    finishedInventory, partNum, vendorName, qty, cost
                )
        elif re.match(COREPATTERN, partNum):
            if qty >= CORE_MIN_QTY:
                _addToInventory(
                    coreInventory, partNum, vendorName, qty, cost
                )

def _buildPerfectionSKUMap(ftp):
    skuMap = {}
    for row in ftp.getFileAsList(r"/perfection/PerfectionFWWMap.csv"):
        perfectionNum = row[0]
        FWWNum = row[1]
        result = skuMap.get(perfectionNum)
        if not result:
            skuMap[perfectionNum] = FWWNum
    return skuMap

def _addPerfectionStock(ftp, coreInventory, finishedInventory):
    perfectionStock = ftp.getFileAsList(r"/perfection/perfection_inventory.xlsx")
    skuMap = _buildPerfectionSKUMap(ftp)
    for row in perfectionStock:
        try:
            status = row[3].lower()[0]
            cost, qty = float(row[6]), int(row[5])
            if cost == cost and qty == qty:
                if status == "c":
                    partNum = skuMap[row[1]][:9]
                    if re.match(COREPATTERN, partNum):
                        _addToInventory(
                            coreInventory, partNum, "Perfection", qty, cost
                        )
                elif status == "f":
                    partNum = skuMap[row[1]]
                    if re.match(FINISHPATTERN, partNum):
                        _addToInventory(
                            coreInventory, partNum, "Perfection", qty, cost
                        )
        except:
            filename = None
            if row[1].count(".") == 3:
                filename = "UnmappedPerfectionSkus_Finished.csv"
            elif row[1]:
                filename = "UnmappedPerfectionSkus_Cores.csv"
            if filename:
                with open(filename, "a", newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([row[1]])

def _addJanteInventory(ftp, finishedInventory):
    jante = ftp.getFileAsList(r"/jante/wheelInventory.csv")
    jantePricingList= ftp.getFileAsList(r"jante/PriceList.xlsx")
    jantePricingDict = {
        row[0]: float(row[1]) for row in jantePricingList if row[1]
    }
    for row in jante:
        partNum = row[0]
        if re.match(REPLICAPATTERN, partNum):
            qty = int(row[1])
            if qty >= FINISHED_MIN_QTY:
                try:
                    cost = jantePricingDict[partNum]
                    partNumExists = finishedInventory.get(partNum)
                    if partNumExists:
                        finishedInventory[partNum]["Jante"] = [qty, cost]
                    else:
                        finishedInventory[partNum] = {"Jante": [qty, cost]}
                except KeyError:
                    print(f"{partNum} has no cost")

def _buildBlackburnsSKUMap(ftp):
    skuMap = {}
    for row in ftp.getFileAsList(r"/blackburns/BlackburnsFWWMap.csv")[2:]:
        blackburnsNum = None
        if row[1].find("-") > 0:
            blackburnsNum = row[1]
        else:
            blackburnsNum = row[1].replace(".", "-")
        FWWNum = row[2]
        result = skuMap.get(blackburnsNum)
        if not result:
            skuMap[blackburnsNum] = FWWNum
    return skuMap

def _addBlackburnsInventory(ftp, finishedInventory):
    blackburns = ftp.getFileAsList(r"/blackburns/BlackburnInventory.csv")
    blackburnsSKUMap = _buildBlackburnsSKUMap(ftp)
    for row in blackburns:
        blackburnsPartNum = row[3]
        grade = row[7]
        qty = int(row[8])
        cost = float(int(row[11]))
        if grade.lower()[0] == "r":
            if qty >= FINISHED_MIN_QTY:
                try:
                    partNum = blackburnsSKUMap.get(blackburnsPartNum)
                    if partNum:
                        partNumExists = finishedInventory.get(partNum)
                        if partNumExists:
                            finishedInventory[partNum]["Blackburns"] = [qty, cost]
                        else:
                            finishedInventory[partNum] = {"Blackburns": [qty, cost]}
                except KeyError:
                    print(f"{partNum} not mapped")

def buildVendorInventory(ftp, fishbowl):
    coreInventory = {}
    finishedInventory = {}
    roadReadyInv = ftp.getFileAsList(r"/roadreadywheels/roadready.csv")
    coastInv = ftp.getFileAsList(r"/lkq/Factory Wheel Warehouse_837903.csv")
    _addWarehouseInventory(fishbowl, coreInventory, finishedInventory)
    _addPartAndCost(0, 3, 2, roadReadyInv, "Road Ready", coreInventory, finishedInventory)
    _addPartAndCost(2, 26, 27, coastInv, "Coast", coreInventory, finishedInventory)
    _addPerfectionStock(ftp, coreInventory, finishedInventory)
    _addJanteInventory(ftp, finishedInventory)
    _addBlackburnsInventory(ftp, finishedInventory)
    return {"Core": coreInventory, "Finished": finishedInventory}

def assignCheapestVendor(partNumber, qty, vendorInventory, orderSource):
    finishedAvailability = vendorInventory["Finished"].get(partNumber)
    coreAvailability = vendorInventory["Core"].get(partNumber[:9])
    vendor = None
    if finishedAvailability:
        min_ = inf
        for vendorName, partInfo in finishedAvailability.items():
            if partInfo[0] >= qty and partInfo[1] < min_:
                min_ = partInfo[1]
                vendor = vendorName
        if vendor and (
            (vendor == "Blackburns" and orderSource == "Ebay Albany") or 
            vendor != "Blackburns"
        ):
            vendorInventory["Finished"][partNumber][vendor][0] -= qty
        else:
            vendor = None
    if (
        not (vendor or coreAvailability) and 
        not re.match(REPLICAPATTERN, partNumber)
    ):
        min_ = inf
        for vendorName, partInfo in coreAvailability.items():
            if partInfo[0] >= qty and partInfo[1] < min_:
                min_ = partInfo[1]
                vendor = vendorName
        if vendor:
            vendorInventory["Core"][partNumber[:9]][vendor][0] -= qty
    return vendor