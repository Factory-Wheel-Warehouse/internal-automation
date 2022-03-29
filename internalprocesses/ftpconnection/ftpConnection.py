from ftplib import FTP
from io import BytesIO
from pandas import read_csv, read_excel

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
    
    def getFileAsList(self, relativePath):
        file = self.getFile(relativePath)
        extension = relativePath[relativePath.find("."):]
        if extension == ".csv":
            return read_csv(file).values.tolist()
        elif extension == ".xlsx":
            return read_excel(file).values.tolist()
    
    def close(self):
        self.server.close()