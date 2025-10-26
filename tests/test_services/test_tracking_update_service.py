from datetime import datetime

import pytest

from src.services.tracking_update_service import TrackingUpdateService


@pytest.fixture
def dependencies(mocker):
    magento = mocker.Mock()
    magento.get_pending_orders.return_value = ["PO123"]
    magento.isWalmartOrder.return_value = False
    magento.getCarrier.return_value = "fedex"

    fishbowl = mocker.Mock()
    fishbowl.isSO.return_value = True
    fishbowl.getPONum.return_value = "PO123"
    fishbowl.getTracking.return_value = None

    outlook = mocker.Mock()
    tracking_checker = mocker.Mock()
    tracking_checker.get_tracking_details.return_value = {
        "data": [{
            "status": "delivered",
            "origin_info": {"ItemReceived": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        }]
    }
    tracking_checker.status_code = 200

    processed_order_dao = mocker.Mock()
    processed_order_dao.get_item.return_value = True

    return magento, fishbowl, outlook, tracking_checker, processed_order_dao


def test_tracking_update_service_processes_orders(mocker, dependencies):
    magento, fishbowl, outlook, tracking_checker, processed_order_dao = dependencies

    service = TrackingUpdateService(
        magento=magento,
        fishbowl=fishbowl,
        outlook=outlook,
        tracking_checker=tracking_checker,
        processed_order_dao=processed_order_dao,
    )
    mocker.patch.object(service, "_get_tracking", return_value={"number": "1Z123", "carrier": "fedex"})

    service.run()

    outlook.login.assert_called_once()
    fishbowl.start.assert_called_once()
    fishbowl.close.assert_called_once()
    magento.addOrderTracking.assert_called_once_with("PO123", "1Z123")
    processed_order_dao.mark_order_shipped.assert_called_once()


def test_get_tracking_falls_back_to_fishbowl(mocker, dependencies):
    magento, fishbowl, outlook, tracking_checker, processed_order_dao = dependencies
    fishbowl.getPONum.return_value = None
    fishbowl.getTracking.return_value = ["TRACK"]

    service = TrackingUpdateService(
        magento=magento,
        fishbowl=fishbowl,
        outlook=outlook,
        tracking_checker=tracking_checker,
        processed_order_dao=processed_order_dao,
    )

    result = service._get_tracking("PO123")
    assert result == {"number": "TRACK", "carrier": "fedex"}


def test_check_tracking_status_retries_when_not_found(mocker, dependencies):
    magento, fishbowl, outlook, tracking_checker, processed_order_dao = dependencies
    responses = [
        {"data": [{"status": "pending"}]},
        {"data": [{"status": "delivered", "origin_info": {"ItemReceived": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}}]},
    ]

    def fake_get_details(*args, **kwargs):
        result = responses.pop(0)
        tracking_checker.status_code = 500 if responses else 200
        return result

    tracking_checker.get_tracking_details.side_effect = fake_get_details
    tracking_checker.status_code = 500

    service = TrackingUpdateService(
        magento=magento,
        fishbowl=fishbowl,
        outlook=outlook,
        tracking_checker=tracking_checker,
        processed_order_dao=processed_order_dao,
    )

    status, received = service._check_tracking_status("TRACK", "fedex", "PO123")
    assert status == "delivered"
    assert isinstance(received, datetime)
    assert tracking_checker.add_single_tracking.called
