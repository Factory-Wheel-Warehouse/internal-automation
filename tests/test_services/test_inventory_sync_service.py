import pandas as pd
import pytest

from src.services.inventory_sync_service import InventorySyncService


@pytest.fixture
def deps(mocker):
    ftp = mocker.Mock()
    fishbowl = mocker.Mock()
    outlook = mocker.Mock()
    inventory = mocker.Mock()
    vendor_dao = mocker.Mock()
    vendor_dao.get_all_items.return_value = ["Vendor"]
    inventory_dao = mocker.Mock()
    return {
        "ftp": ftp,
        "fishbowl": fishbowl,
        "outlook": outlook,
        "inventory": inventory,
        "vendor_dao": vendor_dao,
        "inventory_dao": inventory_dao,
    }


def create_service(deps):
    return InventorySyncService(
        ftp=deps["ftp"],
        fishbowl=deps["fishbowl"],
        outlook=deps["outlook"],
        inventory=deps["inventory"],
        vendor_config_dao=deps["vendor_dao"],
        inventory_dao=deps["inventory_dao"],
    )


def test_publish_master_inventory_builds_and_writes(mocker, deps):
    service = create_service(deps)
    mock_df = pd.DataFrame([{"sku": "ALY12345"}])
    mocker.patch(
        "src.services.inventory_sync_service.build_total_inventory",
        return_value={"ALY12345": {}},
    )
    mocker.patch(
        "src.services.inventory_sync_service.get_initial_dataframe",
        return_value=pd.DataFrame(),
    )
    mocker.patch(
        "src.services.inventory_sync_service.populate_dataframe",
        return_value=mock_df,
    )

    service.publish_master_inventory()

    deps["ftp"].write_df_as_csv.assert_called_once()
    deps["fishbowl"].start.assert_called_once()
    deps["fishbowl"].close.assert_called_once()


def test_sync_dynamo_updates_database(deps):
    service = create_service(deps)
    service.sync_dynamo()
    deps["inventory_dao"].delete_all_items.assert_called_once()
    deps["inventory_dao"].batch_write_items.assert_called_once()


def test_email_master_inventory_sends_mail(deps):
    service = create_service(deps)
    deps["ftp"].get_file_as_binary.return_value = mock_file = type(
        "File", (), {"read": lambda self=None: b"data"}
    )()

    service.email_master_inventory()

    deps["ftp"].start.assert_called_once()
    deps["ftp"].close.assert_called_once()
    deps["outlook"].sendMail.assert_called_once()
