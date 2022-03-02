from ftplib import FTP
from io import BytesIO
from pandas import read_csv

filePath = r"/lkq/Factory Wheel Warehouse_837903.csv"

class FTPConnection():
    
    def __init__(self, host, port, username, password):
        self.server = FTP()
        self.server.connect(host, port)
        self.server.login(username, password)
    
    def getFile(self, relativePath):
        file = BytesIO()
        self.server.retrbinary(f"RETR {relativePath}", file.write)
        file.seek(0)
        return file
    
    def getCSVAsList(self, relativePath):
        file = self.getFile(relativePath)
        return read_csv(file).values.tolist()
    
    def close(self):
        self.server.close()