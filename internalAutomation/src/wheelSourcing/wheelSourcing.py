from math import inf

def _addPartAndCost(
    partColumn, costColumn, qtyColumn, vendorInventory,
    vendorName, inventoryDictionary
):
    for row in vendorInventory:
        partNum = row[partColumn]
        cost, qty = float(row[costColumn]), int(row[qtyColumn])
        if qty > 0:
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
        try:
            status = row[3].lower()[0]
            if status == "c":
                partNum = skuMap[row[1]][:9]
            elif status == "f":
                partNum = skuMap[row[1]]
            cost, qty = float(row[6]), int(row[5])
            if qty > 0:
                if partNum not in inventoryDictionary:
                    inventoryDictionary[partNum] = {"Perfection": [qty, cost]}
                else:
                    inventoryDictionary[partNum]["Perfection"] = [qty, cost]
        except:
            pass

def buildJanteInventory(ftp):
    jante = ftp.getFileAsList(r"/jante/wheelInventory.csv")
    return {row[0]: row[1] for row in jante}

def checkJanteStock(janteStock, partNumber, qty):
    qtyInStock = janteStock.get(partNumber)
    if qtyInStock and qtyInStock >= qty:
        janteStock[partNumber] -= qty
        return True

def buildVendorInventory(ftp):
    combinedInventory = {}
    roadReadyInv = ftp.getFileAsList(r"/roadreadywheels/roadready.csv")
    coastInv = ftp.getFileAsList(r"/lkq/Factory Wheel Warehouse_837903.csv")
    _addPartAndCost(0, 3, 2, roadReadyInv, "Road Ready", combinedInventory)
    _addPartAndCost(2, 26, 27, coastInv, "Coast", combinedInventory)
    _addPerfectionStock(ftp, combinedInventory)
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