import io
from types import SimpleNamespace

import pandas as pd

from src.facade.ftp.ftp_facade import FTPFacade


def test_get_file_as_list_reads_csv(monkeypatch):
    facade = FTPFacade()
    csv_bytes = io.BytesIO(b"col1,col2\n1,2\n3,4\n")
    monkeypatch.setattr(facade, "get_file_as_binary", lambda path: csv_bytes)

    rows = facade.get_file_as_list("file.csv")

    assert rows == [[1, 2], [3, 4]]


def test_get_file_as_list_reads_xlsx(monkeypatch):
    facade = FTPFacade()
    df = pd.DataFrame({"a": [1], "b": [2]})
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    monkeypatch.setattr(facade, "get_file_as_binary", lambda path: buffer)

    rows = facade.get_file_as_list("file.xlsx")

    assert rows == [[1, 2]]


def test_get_directory_most_recent_file_prunes(monkeypatch):
    facade = FTPFacade()
    facade.server = SimpleNamespace()
    facade.server.mlsd = lambda directory, facts=None: [
        ("old.csv", {"modify": "20230101", "type": "file"}),
        ("new.csv", {"modify": "20240101", "type": "file"}),
        ("ignore", {"modify": "20220101", "type": "dir"}),
    ]
    deleted = []

    def fake_delete(path):
        deleted.append(path)

    facade.server.delete = fake_delete
    monkeypatch.setattr(
        facade,
        "get_file_as_list",
        lambda path, encoding="utf-8": [["latest"]],
    )

    rows = facade.get_directory_most_recent_file(
        "/tmp", encoding="latin-1", prune=True
    )

    assert rows == [["latest"]]
    assert deleted == ["/tmp/old.csv"]


def test_write_list_as_csv_uploads_bytes():
    facade = FTPFacade()
    calls = []

    def fake_storbinary(cmd, file_obj):
        calls.append((cmd, file_obj.read()))

    facade.server = SimpleNamespace(storbinary=fake_storbinary)
    facade.write_list_as_csv("/output.csv", [["a", "b"], ["1", "2"]])

    assert calls[0][0] == "STOR /output.csv"
    assert b"a,b\r\n1,2\r\n" in calls[0][1]
