from src.dao.inventory_dao import InventoryDAO
from src.util.aws.dynamodb.constants import INVENTORY_TABLE


def test_inventory_dao_table_config_shapes_primary_keys():
    dao = InventoryDAO()

    assert dao.table_name == INVENTORY_TABLE
    assert dao._partition_key == "sku"
    assert dao._sort_key == "finish_status"

    table_config = dao._table_config
    assert [attr.AttributeName for attr in table_config.AttributeDefinitions] == [
        "sku",
        "finish_status",
    ]
    assert [schema.AttributeName for schema in table_config.KeySchema] == [
        "sku",
        "finish_status",
    ]
