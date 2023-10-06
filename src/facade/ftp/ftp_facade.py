import io
import csv
import os
from ftplib import FTP
from pandas import read_csv, read_excel


class FTPFacade:
    HOST = "54.211.94.170"
    PORT = 21
    USERNAME = "danny"
    PASSWORD = os.getenv("FTP-PW")

    def __init__(self):
        self.server = FTP()

    def start(self):
        self.server.connect(self.HOST, self.PORT)
        self.server.login(self.USERNAME, self.PASSWORD)

    def get_file_as_binary(self, relativePath):
        file = io.BytesIO()
        self.server.retrbinary(f"RETR {relativePath}", file.write)
        file.seek(0)
        return file

    def get_file_as_list(self, relativePath: str, encoding: str = "utf-8"):
        file = self.get_file_as_binary(relativePath)
        extension = relativePath[relativePath.rfind("."):]
        if extension == ".csv":
            csv_file = read_csv(file,
                                quoting=csv.QUOTE_NONE,
                                on_bad_lines="skip",
                                index_col=False,
                                encoding=encoding)
            csv_file.columns = csv_file.columns
            return csv_file.values.tolist()
        elif extension == ".xlsx":
            return read_excel(file,
                              index_col=False).values.tolist()

    def write_list_as_csv(self, outputFilePath, inputList):
        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerows(inputList)
        file_as_bytes = io.BytesIO(csv_file.getvalue().encode())
        self.server.storbinary(f"STOR {outputFilePath}", file_as_bytes)

    def write_df_as_csv(self, outputFilePath, dataframe):
        csv_buffer = io.BytesIO()
        dataframe.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        self.server.storbinary(f"STOR {outputFilePath}", csv_buffer)

    def get_directory_most_recent_file(self, directory: str,
                                       encoding: str = "utf-8",
                                       prune: bool = False):
        newest_file = None
        max_date = 0
        directory_files = list(self.server.mlsd(directory,
                                                facts=["modify", "type"]))
        for file in directory_files:
            file_name, date, type_ = [file[0], int(file[1]["modify"]),
                                      file[1]["type"]]
            if type_ == "file":
                if date > max_date:
                    newest_file = file_name
                    max_date = date
        if prune:
            for file in directory_files:
                file_name, date, type_ = [file[0], file[1]["modify"],
                                          file[1]["type"]]
                if type_ == "file" and file_name != newest_file:
                    self.server.delete(f"{directory}/{file_name}")
        return self.get_file_as_list(f"{directory}/{newest_file}", encoding)

    def close(self):
        self.server.close()
