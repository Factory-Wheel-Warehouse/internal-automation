from dataclasses import dataclass

from flask import request

from src.action.action import Action
from src.services.order_import_service import OrderImportService


@dataclass
class ImportAction(Action):
    order_service: OrderImportService | None = None

    def __post_init__(self):
        if not self.order_service:
            self.order_service = OrderImportService()

    def run(self, request_: request):
        service = self.order_service
        service.prepare_orders()
        service.import_orders(self._is_test(request_))
        email = "orders@factorywheelwarehouse.com"
        if self._is_test(request_):
            email = "danny@factorywheelwarehouse.com"
        service.send_vendor_notifications(email)
        service.send_exception_notifications(email)
        service.close()

    def _is_test(self, request_: request):
        args = self._get_args(request_)
        if args.get("isTest"):
            return bool(args["isTest"])
        return False
