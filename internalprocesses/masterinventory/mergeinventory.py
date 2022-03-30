import os
import csv
from dotenv import load_dotenv
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.wheelsourcing.wheelsourcing import *

def convertInventoryToList(ftpServer):
    combinedInventoryList = []
    inventoryDict = buildVendorInventory(ftpServer)
    janteStock = buildJanteInventory(ftpServer)
    for partNum, qty in janteStock.items():
        if qty:
            if inventoryDict.get(partNum):
                inventoryDict[partNum]["Jante"] = [qty]
            else:
                inventoryDict[partNum] = {"Jante": [qty]}
    total = 0
    for partNum, value in inventoryDict.items():
        if len(str(partNum)) in [9, 11, 12]: # Add 9 to include cores
            qty = sum(
                [vendorDetails[0] for vendorDetails in value.values()]
            )
            if qty:
                combinedInventoryList.append([partNum, qty, ", ".join(list(value.keys()))])
            total += qty
    print(total)
    return combinedInventoryList