from datetime import date
from io import BytesIO

from src.action.inventory.email_action import EmailAction
from src.util.constants.inventory import MASTER_INVENTORY_PATH


def test_email_action_sends_encoded_inventory_file(mocker):
    ftp = mocker.Mock()
    outlook = mocker.Mock()
    file_bytes = BytesIO(b"csv-data")
    ftp.get_file_as_binary.return_value = file_bytes
    mocker.patch("src.action.inventory.email_action.date", wraps=date)

    action = EmailAction(ftp=ftp, outlook_facade=outlook)
    action.run(request_=None)

    ftp.start.assert_called_once()
    outlook.login.assert_called_once()
    ftp.get_file_as_binary.assert_called_once_with(MASTER_INVENTORY_PATH)
    outlook.sendMail.assert_called_once()
    ftp.close.assert_called_once()
