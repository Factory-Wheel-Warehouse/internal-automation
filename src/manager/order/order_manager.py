from src.facade.internal_automation_facade.internal_automation_facade import \
    InternalAutomationFacade
from src.manager.manager import Manager
from src.manager.order.order_notification_manager import \
    OrderNotificationManager


class OrderManager(Manager):

    @property
    def endpoint(self):
        return "order"

    @Manager.sub_manager
    def notification(self):
        return OrderNotificationManager()

    @Manager.action
    @Manager.asynchronous()
    def import_new(self):
        automation = InternalAutomationFacade()
        automation.getOrders()
        automation.importOrders()
        email = "orders@factorywheelwarehouse.com"
        for vendor in automation.ordersByVendor:
            automation.emailDropships(automation.ordersByVendor[vendor],
                                      vendor, email)
        automation.emailExceptionOrders(email)
        automation.close()

    @Manager.action
    @Manager.asynchronous()
    def import_test(self):
        automation = InternalAutomationFacade()
        automation.getOrders()
        automation.importOrders(test=True)
        email = "danny@factorywheelwarehouse.com"
        for vendor in automation.ordersByVendor:
            automation.emailDropships(automation.ordersByVendor[vendor],
                                      vendor, email)
        automation.emailExceptionOrders(email)
        automation.close()
