from types import SimpleNamespace

import pytest

from src.action.order.import_action import ImportAction
from src.action.order.notify_action import NotifyAction
from src.action.report.quatity_sold_action import QuantitySoldAction


class DummyRequest:
    def __init__(self, args=None):
        self.args = SimpleNamespace(to_dict=lambda: args or {})


def test_import_action_run_handles_test_flag(mocker):
    service = mocker.patch(
        "src.action.order.import_action.OrderImportService",
    ).return_value

    action = ImportAction()
    action.run(DummyRequest({"isTest": True}))

    service.prepare_orders.assert_called_once()
    service.import_orders.assert_called_with(True)
    service.send_vendor_notifications.assert_called_with("danny@factorywheelwarehouse.com")
    service.send_exception_notifications.assert_called_with("danny@factorywheelwarehouse.com")
    service.close.assert_called_once()


def test_import_action_non_test_defaults_to_sales_email(mocker):
    service = mocker.patch(
        "src.action.order.import_action.OrderImportService"
    ).return_value

    ImportAction().run(DummyRequest())

    service.import_orders.assert_called_with(False)
    service.send_exception_notifications.assert_called_with("orders@factorywheelwarehouse.com")


def _make_order(**overrides):
    base = {
        "shipped": False,
        "account": "amazon",
        "customer_po": "PO123",
        "address": SimpleNamespace(name="Customer"),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_notify_action_sends_email_for_upcoming_orders(mocker):
    outlook = mocker.Mock()
    dao = mocker.Mock()
    dao.get_orders_by_sbd.side_effect = [
        [_make_order()],
        [_make_order(customer_po="PO999", account="ebay")],
    ]

    action = NotifyAction(outlook=outlook, order_dao=dao)
    action.run(DummyRequest())

    outlook.login.assert_called_once()
    assert outlook.sendMail.called
    args, kwargs = outlook.sendMail.call_args
    assert "Ship By" in args[1]
    assert "<li>Amazon order #PO123 - Customer</li>" in args[2]
    assert "<li>Ebay order #PO999 - Customer</li>" in args[2]


def test_quantity_sold_action_builds_and_sends_report(mocker):
    outlook = mocker.Mock()
    fishbowl = mocker.Mock()
    mocker.patch(
        "src.action.report.quatity_sold_action.quantity_sold_by_sku_report",
        return_value=[["SKU1", 5]],
    )

    action = QuantitySoldAction(outlook=outlook, fishbowl=fishbowl)
    action.run(DummyRequest())

    fishbowl.start.assert_called_once()
    fishbowl.close.assert_called_once()
    assert outlook.sendMail.called
    attachment = outlook.sendMail.call_args.kwargs["attachment"]
    decoded = __import__("base64").b64decode(attachment.encode()).decode()
    assert "SKU1,5" in decoded
