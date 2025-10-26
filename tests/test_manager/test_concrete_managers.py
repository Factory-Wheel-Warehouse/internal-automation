from types import SimpleNamespace

from src.action.action import Action
from src.manager.inventory.inventory_manager import InventoryManager
from src.manager.order.order_manager import OrderManager
from src.manager.report_manager.report_manager import ReportManager
from src.manager.scraping.scraping_manager import ScrapingManager
from src.manager.tracking.tracking_manager import TrackingManager


class DummyAction(Action):
    @property
    def async_(self):
        return False

    def run(self, request_):
        return {"ok": True}


def test_scraping_manager_lists_parts_trader_route(mocker):
    mocker.patch("src.manager.scraping.scraping_manager.PartsTraderAction", DummyAction)
    manager = ScrapingManager()
    assert manager.list()["actions"] == ["dummy"]


def test_tracking_manager_lists_upload_action(mocker):
    mocker.patch("src.manager.tracking.tracking_manager.UploadAction", DummyAction)
    manager = TrackingManager()
    assert manager.list()["actions"] == ["dummy"]


def test_order_manager_registers_actions(mocker):
    mocker.patch("src.manager.order.order_manager.ImportAction", DummyAction)
    mocker.patch("src.manager.order.order_manager.NotifyAction", DummyAction)
    manager = OrderManager()
    routes = manager.list()["actions"]
    assert routes == ["dummy", "dummy"]


def test_report_manager_lists_quantity_action(mocker):
    mocker.patch("src.manager.report_manager.report_manager.QuantitySoldAction", DummyAction)
    manager = ReportManager()
    assert manager.list()["actions"] == ["dummy"]


def test_inventory_manager_registers_email_action_and_sub_manager(mocker):
    mocker.patch("src.manager.inventory.inventory_manager.EmailAction", DummyAction)
    upload_stub = SimpleNamespace(
        blueprint=SimpleNamespace(),
        name="upload",
        list=lambda: {"actions": ["ftp"]},
    )
    mocker.patch("src.manager.inventory.inventory_manager.UploadManager", return_value=upload_stub)
    manager = InventoryManager()
    listing = manager.list()
    assert listing["actions"] == ["dummy"]
    assert "upload" in listing["managers"]
