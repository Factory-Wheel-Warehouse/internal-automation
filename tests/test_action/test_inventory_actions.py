from types import SimpleNamespace

# Importing the module ensures DynamoAction is evaluated with patched boto3
import src.action.inventory.upload.dynamo_action as dynamo_action_module
from src.action.inventory.upload.ftp_action import FtpAction
from src.action.inventory.upload.pricing_action import PricingAction
from src.domain.inventory.inventory import Inventory


def test_dynamo_action_builds_inventory_and_persists(mocker):
    inventory = mocker.create_autospec(Inventory, instance=True)
    ftp = mocker.Mock()
    fishbowl = mocker.Mock()
    inventory.convert_to_entries.return_value = ["entry"]
    action = dynamo_action_module.DynamoAction(
        ftp=ftp,
        fishbowl_facade=fishbowl,
        inventory=inventory,
        inventory_dao=mocker.Mock()
    )

    action.run(request_=None)

    fishbowl.start.assert_called_once()
    ftp.start.assert_called_once()
    inventory.build.assert_called_once_with(ftp, fishbowl)
    action.inventory_dao.delete_all_items.assert_called_once()
    action.inventory_dao.batch_write_items.assert_called_once_with(["entry"])


def test_ftp_action_generates_master_inventory(mocker):
    ftp = mocker.Mock()
    fishbowl = mocker.Mock()
    inventory = mocker.create_autospec(Inventory, instance=True)
    vendor_dao = mocker.Mock()
    vendor_configs = ["v1", "v2"]
    vendor_dao.get_all_items.return_value = vendor_configs
    mocker.patch(
        "src.action.inventory.upload.ftp_action.build_total_inventory",
        return_value={"key": "value"},
    )
    mocker.patch(
        "src.action.inventory.upload.ftp_action.get_initial_dataframe",
        return_value="df",
    )
    mocker.patch(
        "src.action.inventory.upload.ftp_action.populate_dataframe",
        return_value="final_df",
    )

    action = FtpAction(
        ftp=ftp,
        fishbowl_facade=fishbowl,
        inventory=inventory,
        vendor_config_dao=vendor_dao,
    )

    action.run(request_=None)

    ftp.start.assert_called_once()
    fishbowl.start.assert_called_once()
    inventory.build.assert_called_once_with(ftp, fishbowl)
    ftp.write_df_as_csv.assert_called_once()
    ftp.close.assert_called_once()
    fishbowl.close.assert_called_once()


def test_pricing_action_builds_price_list(mocker):
    ftp = mocker.Mock()
    vendor_dao = mocker.Mock()
    vendor_config = SimpleNamespace(
        cost_adjustment_config="adjust",
        sku_map_config=SimpleNamespace(file_path="map.csv"),
    )
    vendor_dao.get_item.return_value = vendor_config
    mocker.patch(
        "src.action.inventory.upload.pricing_action.get_sku_map",
        return_value={"PN1": "SKU1"},
    )
    mocker.patch(
        "src.action.inventory.upload.pricing_action.get_adjusted_cost",
        return_value=12.0,
    )
    mocker.patch(
        "src.action.inventory.upload.pricing_action.get_list_price",
        return_value=["SKU1", 15.0],
    )
    ftp.get_file_as_list.return_value = [["PN1", 10.0]]

    action = PricingAction(ftp=ftp, vendor_config_dao=vendor_dao)
    action.run(request_=None)

    ftp.write_list_as_csv.assert_called_once()
    ftp.close.assert_called_once()
