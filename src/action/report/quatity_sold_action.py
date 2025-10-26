from dataclasses import dataclass

from flask import request

from src.action.action import Action
from src.services.reporting_service import ReportingService


@dataclass
class QuantitySoldAction(Action):
    reporting_service: ReportingService | None = None

    def __post_init__(self):
        if not self.reporting_service:
            self.reporting_service = ReportingService()

    def run(self, request_: request):
        self.reporting_service.send_quantity_sold_report()
