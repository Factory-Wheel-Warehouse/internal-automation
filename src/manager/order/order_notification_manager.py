from datetime import date
from datetime import timedelta

from src.dao.processed_order_dao import ProcessedOrderDAO
from src.domain.order.order import Order
from src.facade.outlook import OutlookFacade
from src.manager.manager import Manager
from src.util.logging import log_exceptions


class OrderNotificationManager(Manager):
    outlook: OutlookFacade = OutlookFacade()
    order_dao: ProcessedOrderDAO = ProcessedOrderDAO()

    @property
    def endpoint(self):
        return "notification"

    @Manager.action
    @Manager.asynchronous()
    @log_exceptions
    def ship_by(self):
        self.outlook.login()
        orders_to_notify_by_offset = {}
        for day_offset in range(2):
            ship_by_date = str(date.today() + timedelta(days=day_offset))
            orders = self.order_dao.get_orders_by_sbd(ship_by_date)
            unshipped_orders = filter(lambda order: not order.shipped, orders)
            orders_to_notify_by_offset[day_offset] = list(unshipped_orders)

        message = self._get_sbd_message(orders_to_notify_by_offset)
        if message:
            self.outlook.sendMail("orders@factorywheelwarehouse.com",
                                  "\"Ship By\" Automated Notifications",
                                  message, contentType="HTML")

    @staticmethod
    def _get_sbd_message(orders_by_offset: dict[int, list[Order]]) -> str:
        message_lines = []
        for offset, orders in orders_by_offset.items():
            if offset == 0:
                message_lines.append(f"<p>Orders due to ship today:</p>")
            else:
                message_lines.append(f"<p>Orders due to ship in "
                                     f"{offset} day(s):</p>")
            message_lines.append("<ul>")
            for order in orders:
                order_string = f"{order.account.capitalize()} order #" \
                               f"{order.customer_po} - {order.address.name}"
                message_lines.append(f"<li>{order_string}</li>")
            message_lines.append("</ul>")
        return "".join(message_lines)
