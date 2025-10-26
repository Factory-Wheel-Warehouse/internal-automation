from types import SimpleNamespace

from src.action.order.notify_action import NotifyAction


def _order(**overrides):
    base = {
        "shipped": False,
        "account": "amazon",
        "customer_po": "PO123",
        "address": SimpleNamespace(name="Customer"),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_notify_action_sends_email(mocker):
    outlook = mocker.Mock()
    dao = mocker.Mock()
    dao.get_orders_by_sbd.side_effect = [[_order()], [_order(customer_po="PO999", account="ebay")]]

    action = NotifyAction(outlook=outlook, order_dao=dao)
    action.run(request_=None)

    outlook.login.assert_called_once()
    assert outlook.sendMail.called
    args, kwargs = outlook.sendMail.call_args
    assert "Ship By" in args[1]
    assert "Amazon order #PO123" in args[2]
