import logging
import sys
from datetime import date

import watchtower
from flask import Flask

from src.manager.inventory.inventory_manager import InventoryManager
from src.manager.manager import Manager
from src.manager.order.order_manager import OrderManager
from src.manager.report_manager.report_manager import ReportManager
from src.manager.scraping.scraping_manager import ScrapingManager
from src.manager.tracking import TrackingManager
from src.util.aws import boto3_session
from src.util.constants.aws import DEFAULT_REGION
from src.util.logging import set_up_logging


class Server(Flask):
    service_name: str = "InternalAutomationService"
    service_root: str = "/ms/"
    managers: list[Manager] = [
        InventoryManager(),
        OrderManager(),
        ReportManager(),
        ScrapingManager(),
        TrackingManager()
    ]
    _registry: dict = None

    @property
    def registry(self):
        if not self._registry:
            return {m.name: m.list() for m in self.managers}
        else:
            return self._registry

    def __init__(self):
        set_up_logging()

        super().__init__(self.service_name)

        self.add_url_rule(
            self.service_root,
            view_func=lambda: self.registry
        )

        for manager in self.managers:
            self.register_blueprint(manager.blueprint)


server = Server()

logging.info(f"Starting {server.service_name}")

if __name__ == "__main__":
    server.run(debug=True)
