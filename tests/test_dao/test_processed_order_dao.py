from src.dao.processed_order_dao import ProcessedOrderDAO
from src.util.aws.dynamodb.constants import (
    ATTRIBUTE_VALUE_LIST_KEY,
    COMPARISON_OPERATOR_KEY,
    EQUAL_TO,
)


def test_get_orders_by_sbd_builds_scan_filter(mocker):
    dao = ProcessedOrderDAO()
    mocker.patch.object(ProcessedOrderDAO, "_marshall", side_effect=lambda data: data)
    get_all = mocker.patch.object(ProcessedOrderDAO, "get_all_items", return_value=["order"])

    result = dao.get_orders_by_sbd("2024-02-02")

    assert result == ["order"]
    get_all.assert_called_once_with(
        ship_by_date={
            ATTRIBUTE_VALUE_LIST_KEY: ["2024-02-02"],
            COMPARISON_OPERATOR_KEY: EQUAL_TO,
        }
    )


def test_mark_order_shipped_updates_expected_fields(mocker, freezer):
    freezer.move_to("2024-03-05")
    dao = ProcessedOrderDAO()
    update_item = mocker.patch.object(ProcessedOrderDAO, "_update_item", return_value=None)

    dao.mark_order_shipped("PO-123")

    update_item.assert_called_once_with(
        "PO-123",
        [("shipped", True), ("date_shipped", "2024-03-05")],
    )
