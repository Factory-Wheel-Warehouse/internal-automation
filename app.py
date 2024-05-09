from dataclasses import dataclass

from flask import Flask

from src.manager.inventory.inventory_manager import InventoryManager
from src.manager.manager import Manager
from src.manager.order.order_manager import OrderManager
from src.manager.report_manager.report_manager import ReportManager
from src.manager.tracking import TrackingManager
from src.util.logging import logger


@dataclass
class FlaskService:
    manager: Manager


@dataclass
class FlaskServer:
    app: Flask
    managers: list[Manager]

    def __post_init__(self):
        for service in services:
            self._add_routes(service)
        self.structure = self._get_route_structure()
        self.app.add_url_rule("/ms/", view_func=lambda: self.structure)

    def _get_route_structure(self, managers=None, indent=0,
                             indent_seq="&emsp;"):
        structure = []
        if not managers and not indent:
            managers = self.managers
        for manager in managers:
            structure.append((indent_seq * indent) + manager.endpoint)
            for route in manager.get_actions():
                structure.append((indent_seq * (indent + 1)) + route)
            structure += self._get_route_structure(manager.get_sub_managers(),
                                                   indent=1).splitlines()
        return r"<br \>".join(structure)

    @staticmethod
    def get_url(resource_path: list[str]):
        return "/" + "/".join(resource_path)

    def _add_routes(self, manager: Manager, prefix: list[str] = None):
        if prefix is None:
            path = ["ms", manager.endpoint]
        else:
            path = prefix + [manager.endpoint]
        for name in manager.get_actions():
            route = path + [name]
            func = getattr(manager, name)
            self.app.add_url_rule(self.get_url(route), view_func=func)
        for sub_manager in manager.get_sub_managers():
            self._add_routes(sub_manager, prefix=path)


app = Flask("InternalAutomationService")

services = [
    InventoryManager(),
    OrderManager(),
    TrackingManager(),
    ReportManager()
]
server = FlaskServer(app, services)

if __name__ == "__main__":
    logger.info("Starting InternalAutomationService application")
    app.run(debug=True)
