import io
import csv
from ftplib import FTP
from pandas import read_csv, read_excel

class FTPConnection():
    
    def __init__(self, host, port, username, password):
        self.server = FTP()
        self.server.connect(host, port)
        self.server.login(username, password)
    
    def getFileAsBinary(self, relativePath):
        file = io.BytesIO()
        self.server.retrbinary(f"RETR {relativePath}", file.write)
        file.seek(0)
        return file
    
    def getFileAsList(self, relativePath):
        file = self.getFileAsBinary(relativePath)
        extension = relativePath[relativePath.find("."):]
        if extension == ".csv":
            return read_csv(file, on_bad_lines="skip").values.tolist()
        elif extension == ".xlsx":
            return read_excel(file).values.tolist()
    
    def writeListAsCSV(self, outputFilePath, inputList):
        csvFile = io.StringIO()
        writer = csv.writer(csvFile)
        writer.writerows(inputList)
        fileAsBytes = io.BytesIO(csvFile.getvalue().encode())
        self.server.storbinary(f"STOR {outputFilePath}", fileAsBytes)
    
    def close(self):
        self.server.close()