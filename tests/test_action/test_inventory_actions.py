from src.action.inventory.email_action import EmailAction
from src.action.inventory.upload.dynamo_action import DynamoAction
from src.action.inventory.upload.ftp_action import FtpAction
from src.action.report.quatity_sold_action import QuantitySoldAction


def test_ftp_action_uses_inventory_service(mocker):
    service = mocker.patch("src.action.inventory.upload.ftp_action.InventorySyncService").return_value
    FtpAction().run(request_=None)
    service.publish_master_inventory.assert_called_once()


def test_dynamo_action_uses_inventory_service(mocker):
    service = mocker.patch("src.action.inventory.upload.dynamo_action.InventorySyncService").return_value
    DynamoAction().run(request_=None)
    service.sync_dynamo.assert_called_once()


def test_email_action_uses_inventory_service(mocker):
    service = mocker.patch("src.action.inventory.email_action.InventorySyncService").return_value
    EmailAction().run(request_=None)
    service.email_master_inventory.assert_called_once()


def test_quantity_sold_action_uses_reporting_service(mocker):
    reporting = mocker.patch(
        "src.action.report.quatity_sold_action.ReportingService"
    ).return_value
    QuantitySoldAction().run(request_=None)
    reporting.send_quantity_sold_report.assert_called_once()
