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
        super().__init__(self.service_name)

        self.add_url_rule(
            self.service_root,
            view_func=lambda: self.registry
        )

        for manager in self.managers:
            self.register_blueprint(manager.blueprint)


LOGGING_CONFG = {
    "handlers": [
        watchtower.CloudWatchLogHandler(
            boto3_client=boto3_session.client(
                "logs", region_name=DEFAULT_REGION
            ),
            log_group_name="/ext/heroku/InternalAutomationService",
            log_stream_name=f"application.{date.today().isoformat()}.log"
        ),
        logging.StreamHandler(sys.stdout)
    ],
    "level": "INFO"
}

server = Server()

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(**LOGGING_CONFG)

    logging.info("Starting InternalAutomationService application")

    server.run(debug=True)
