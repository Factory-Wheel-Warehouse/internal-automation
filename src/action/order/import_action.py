from dataclasses import dataclass

from flask import request

from src.action.action import Action
from src.facade.internal_automation_facade.internal_automation_facade import \
    InternalAutomationFacade


@dataclass
class ImportAction(Action):

    def run(self, request_: request):
        self._is_test(request_)
        automation = InternalAutomationFacade()
        automation.getOrders()
        automation.importOrders(self._is_test(request_))
        email = "orders@factorywheelwarehouse.com"
        for vendor in automation.ordersByVendor:
            automation.emailDropships(automation.ordersByVendor[vendor],
                                      vendor, email)
        automation.emailExceptionOrders(email)
        automation.close()

    def _is_test(self, request_: request):
        args = self._get_args(request_)
        if args.get("isTest"):
            return bool(args["isTest"])
        return False
