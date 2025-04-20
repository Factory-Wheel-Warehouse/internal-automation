from dataclasses import dataclass

from flask import request

from src.action.action import Action
from src.facade.internal_automation_facade.internal_automation_facade import \
    InternalAutomationFacade


@dataclass
class UploadAction(Action):

    def run(self, request_: request):
        automation = InternalAutomationFacade()
        automation.addTracking()
        automation.close()
