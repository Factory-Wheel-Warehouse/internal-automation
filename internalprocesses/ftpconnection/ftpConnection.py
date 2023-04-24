import io
import csv
from ftplib import FTP
from pandas import read_csv, read_excel


class FTPConnection:

    def __init__(self, host, port, username, password):
        self.server = FTP()
        self.server.connect(host, port)
        self.server.login(username, password)

    def get_file_as_binary(self, relativePath):
        file = io.BytesIO()
        self.server.retrbinary(f"RETR {relativePath}", file.write)
        file.seek(0)
        return file

    def get_file_as_list(self, relativePath):
        file = self.get_file_as_binary(relativePath)
        extension = relativePath[relativePath.rfind("."):]
        if extension == ".csv":
            return read_csv(file,
                            quoting=csv.QUOTE_NONE,
                            on_bad_lines="skip").values.tolist()
        elif extension == ".xlsx":
            return read_excel(file).values.tolist()

    def write_list_as_csv(self, outputFilePath, inputList):
        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerows(inputList)
        file_as_bytes = io.BytesIO(csv_file.getvalue().encode())
        self.server.storbinary(f"STOR {outputFilePath}", file_as_bytes)

    def get_directory_most_recent_file(self, directory: str,
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
        return self.get_file_as_list(f"{directory}/{newest_file}")

    def close(self):
        self.server.close()
