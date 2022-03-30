import os
import csv
from dotenv import load_dotenv
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.wheelsourcing.wheelsourcing import *
from internalprocesses.masterinventory.mergeinventory import convertInventoryToList


load_dotenv()

password = os.getenv("FTP-PW")

server = FTPConnection("54.211.94.170", 21, "danny", password)

masterInventoryList = convertInventoryToList(server)

with open("mergedInventory.csv", "w+", newline = '') as file:
    writer = csv.writer(file)
    writer.writerows(masterInventoryList)