import logging
import sys
from datetime import date

import watchtower
from flask import Flask

from src.manager.inventory.inventory_manager import InventoryManager
from src.manager.order.order_manager import OrderManager
from src.manager.report_manager.report_manager import ReportManager
from src.manager.scraping.scraping_manager import ScrapingManager
from src.manager.tracking import TrackingManager
from src.util.aws import boto3_session
from src.util.constants.aws import DEFAULT_REGION

app = Flask("InternalAutomationService")

services = [
    InventoryManager(),
    OrderManager(),
    ReportManager(),
    ScrapingManager(),
    TrackingManager()
]

app.add_url_rule("/ms/", view_func=lambda: [m.name for m in services])

for manager in services:
    app.register_blueprint(manager.blueprint)

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        handlers=[
            watchtower.CloudWatchLogHandler(
                boto3_client=boto3_session.client(
                    "logs", region_name=DEFAULT_REGION
                ),
                log_group_name="/ext/heroku/InternalAutomationService",
                log_stream_name=f"application.{date.today().isoformat()}.log"
            ),
            logging.StreamHandler(sys.stdout)
        ],
        level="INFO"
    )

    print("Starting InternalAutomationService application")

    app.run(debug=True)
