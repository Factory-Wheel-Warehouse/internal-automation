from src.facade.internal_automation_facade.internal_automation_facade import \
    InternalAutomationFacade
from src.manager.manager import Manager
from src.util.logging.sns_exception_logging_decorator import log_exceptions


class TrackingManager(Manager):

    @property
    def endpoint(self):
        return "tracking"

    @Manager.action
    @Manager.asynchronous()
    @log_exceptions
    def upload_pending(self):
        automation = InternalAutomationFacade()
        automation.addTracking()
        automation.close()
