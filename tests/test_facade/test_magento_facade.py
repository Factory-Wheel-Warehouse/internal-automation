import pytest

from src.facade.magento.magento_facade import Environment, MagentoFacade


def test_build_search_criteria_populates_params():
    facade = MagentoFacade()
    params = {}

    facade.build_search_criteria(params, "status", "processing", "eq", group=2)

    base = "searchCriteria[filter_groups][2][filters][0]"
    assert params[base + "[field]"] == "status"
    assert params[base + "[value]"] == "processing"
    assert params[base + "[condition_type]"] == "eq"


@pytest.mark.parametrize(
    "increment_id,expected",
    [
        ("1000001234", "website"),
        ("123456789012345", "walmart"),
        ("A12-12345-12345", "ebay"),
        ("123-1234567-1234567", "amazon"),
    ],
)
def test_get_platform_matches_patterns(increment_id, expected):
    facade = MagentoFacade()
    assert facade.get_platform(increment_id) == expected


def test_build_shipment_upload_payload_adds_items_and_tracks():
    facade = MagentoFacade()
    order = {
        "increment_id": "1000001234",
        "items": [
            {"item_id": 1, "qty_ordered": 2, "qty_shipped": 0},
            {"item_id": 2, "qty_ordered": 1, "qty_shipped": 1},
        ],
    }
    payload = facade.buildShipmentUploadPayload(
        carrier="ups", title="UPS", trackingNumber="1Z123",
        order=order
    )

    assert payload["items"] == [{"order_item_id": 1, "qty": 2}]
    assert payload["tracks"][0]["track_number"] == "1Z123"


def test_add_order_tracking_posts_when_payload_ready(mocker):
    facade = MagentoFacade()
    order_details = {
        "increment_id": "1000001234",
        "items": [
            {
                "order_id": 42,
                "item_id": 5,
                "qty_ordered": 2,
                "qty_shipped": 0,
            }
        ],
    }
    mocker.patch.object(
        facade, "get_order_details", return_value=order_details
    )
    mocker.patch.object(
        facade, "trackingNumberCarrier", return_value=("ups", "UPS")
    )
    mocker.patch.object(facade, "getCarrier", return_value="ups")
    mock_post = mocker.patch(
        "src.facade.magento.magento_facade.requests.post", return_value="ok"
    )

    facade.addOrderTracking("1000001234", "1Z1234567890123456")

    mock_post.assert_called_once()
    url = mock_post.call_args.kwargs["url"]
    assert url.endswith("/order/42/ship")
