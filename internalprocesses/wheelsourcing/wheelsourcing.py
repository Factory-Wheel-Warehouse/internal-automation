import re
import csv
from math import inf

FINISHPATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}[0-9]{2}$"
REPLICAPATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}[0-9]{2}N{1}$"
COREPATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}$"
ROADREADYREPLICAPATTERN = r"(ALY|STL|FWC)[0-9]{6}[A-Z]{1}[0-9]{2}N{1}$"
FWWCOREPATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}[0-9]{2}\*CORE$"

CORE_MIN_QTY = 5
FINISHED_MIN_QTY = 3

def _formatWarehouseSKU(partNum):
    partNum = partNum.upper()
    if re.search(FINISHPATTERN, partNum):
        return partNum
    if re.search(REPLICAPATTERN, partNum):
        return partNum
    if re.search(FWWCOREPATTERN, partNum):
        return partNum[:9]

def _addWarehouseInventory(fishbowl, inventoryDictionary):
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
            if partNum not in inventoryDictionary:
                inventoryDictionary[partNum] = {"Warehouse": [qty, avgCost]}
            else:
                inventoryDictionary[partNum]["Warehouse"] = [qty, avgCost]

def _addPartAndCost(
    partColumn, costColumn, qtyColumn, vendorInventory,
    vendorName, inventoryDictionary
):
    for row in vendorInventory:
        partNum = row[partColumn]
        if re.match(ROADREADYREPLICAPATTERN, partNum) and partNum[3] == "0":
            partNum = partNum[:3] + partNum[4:]
        minRequiredQty = 0
        if (
            re.match(FINISHPATTERN, partNum) or 
            re.match(REPLICAPATTERN, partNum)
        ):  
            minRequiredQty = FINISHED_MIN_QTY
        elif re.match(COREPATTERN, partNum):
            minRequiredQty = CORE_MIN_QTY
        cost, qty = float(row[costColumn]), int(row[qtyColumn])
        if minRequiredQty and qty > minRequiredQty:
            if vendorName == "Coast":
                if str(partNum)[:3] == "ALY":
                    cost += 12.50
                elif str(partNum)[:3] == "STL":
                    cost += 17.50
            if partNum not in inventoryDictionary:
                inventoryDictionary[partNum] = {vendorName: [qty, cost]}
            else:
                inventoryDictionary[partNum][vendorName] = [qty, cost]

def _buildSKUMap(ftp):
    skuMap = {}
    for row in ftp.getFileAsList(r"/perfection/PerfectionFWWMap.csv"):
        perfectionNum = row[0]
        FWWNum = row[1]
        result = skuMap.get(perfectionNum)
        if not result:
            skuMap[perfectionNum] = FWWNum
    return skuMap

def _addPerfectionStock(ftp, inventoryDictionary):
    perfectionStock = ftp.getFileAsList(r"/perfection/perfection_inventory.xlsx")
    skuMap = _buildSKUMap(ftp)
    for row in perfectionStock:
        minRequiredQty = 0
        try:
            status = row[3].lower()[0]
            if status == "c":
                minRequiredQty = CORE_MIN_QTY
                partNum = skuMap[row[1]][:9]
            elif status == "f":
                minRequiredQty = FINISHED_MIN_QTY
                partNum = skuMap[row[1]]
            cost, qty = float(row[6]), int(row[5])
            if qty >= minRequiredQty:
                if partNum not in inventoryDictionary:
                    inventoryDictionary[partNum] = {"Perfection": [qty, cost]}
                else:
                    inventoryDictionary[partNum]["Perfection"] = [qty, cost]
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

def _addJanteInventory(ftp, inventoryDictionary):
    jante = ftp.getFileAsList(r"/jante/wheelInventory.csv")
    jantePricingList= ftp.getFileAsList(r"jante/PriceList.xlsx")
    jantePricingDict = {
        row[0]: float(row[1]) for row in jantePricingList if row[1]
    }
    for row in jante:
        partNum = row[0]
        if re.match(REPLICAPATTERN, partNum):
            qty = int(row[1])
            if qty >= CORE_MIN_QTY:
                try:
                    cost = jantePricingDict[partNum]
                    partNumExists = inventoryDictionary.get(partNum)
                    if partNumExists:
                        inventoryDictionary[partNum]["Jante"] = [qty, cost]
                    else:
                        inventoryDictionary[partNum] = {"Jante": [qty, cost]}
                except KeyError:
                    pass

def buildVendorInventory(ftp, fishbowl):
    combinedInventory = {}
    roadReadyInv = ftp.getFileAsList(r"/roadreadywheels/roadready.csv")
    coastInv = ftp.getFileAsList(r"/lkq/Factory Wheel Warehouse_837903.csv")
    _addWarehouseInventory(fishbowl, combinedInventory)
    _addPartAndCost(0, 3, 2, roadReadyInv, "Road Ready", combinedInventory)
    _addPartAndCost(2, 26, 27, coastInv, "Coast", combinedInventory)
    _addPerfectionStock(ftp, combinedInventory)
    _addJanteInventory(ftp, combinedInventory)
    return combinedInventory

def assignCheapestVendor(partNumber, qty, vendorInventory):
    wheelAvailability = vendorInventory.get(partNumber)
    vendor = None
    if wheelAvailability:
        min_ = inf
        for vendorName, partInfo in wheelAvailability.items():
            if partInfo[0] >= qty and partInfo[1] < min_:
                min_ = partInfo[1]
                vendor = vendorName
    if vendor:
        vendorInventory[partNumber][vendor][0] -= qty
    return vendor