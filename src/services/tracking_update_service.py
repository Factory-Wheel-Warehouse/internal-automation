import logging
from datetime import datetime, timedelta

from src.dao.processed_order_dao import ProcessedOrderDAO
from src.facade.fishbowl import FishbowlFacade
from src.facade.magento.magento_facade import MagentoFacade
from src.facade.outlook import OutlookFacade
from src.util.tracking.tracking_checker import TrackingChecker
from src.util.tracking.util import get_tracking_from_outlook


class TrackingUpdateService:
    """
    Coordinates tracking-number retrieval and fulfillment updates across Magento,
    Fishbowl, Outlook, and Tracktry.
    """

    def __init__(
            self,
            magento: MagentoFacade | None = None,
            fishbowl: FishbowlFacade | None = None,
            outlook: OutlookFacade | None = None,
            tracking_checker: TrackingChecker | None = None,
            processed_order_dao: ProcessedOrderDAO | None = None,
            logger: logging.Logger | None = None,
    ):
        self.magento = magento or MagentoFacade()
        self.fishbowl = fishbowl or FishbowlFacade()
        self.outlook = outlook or OutlookFacade()
        self.tracking_checker = tracking_checker or TrackingChecker()
        self.processed_order_dao = processed_order_dao or ProcessedOrderDAO()
        self.logger = logger or logging.getLogger(__name__)

    def run(self):
        """
        Fetch unfulfilled Magento orders, locate available tracking numbers,
        and update Magento / ProcessedOrder records accordingly.
        """
        self.outlook.login()
        self.fishbowl.start()
        try:
            unfulfilled_orders = self.magento.get_pending_orders()
            tracking_candidates = self._collect_tracking_candidates(unfulfilled_orders)
            self._process_tracking_updates(tracking_candidates)
        finally:
            self.fishbowl.close()

    # --- internal helpers -------------------------------------------------

    def _collect_tracking_candidates(self, unfulfilled_orders: list[str]) -> dict[str, str]:
        tracking = {}
        for customer_po in unfulfilled_orders:
            if self.magento.isWalmartOrder(customer_po):
                continue
            tracking_num = self._get_tracking(customer_po)
            if tracking_num:
                tracking[customer_po] = tracking_num
        self.logger.info(
            "Found tracking numbers for %s of %s orders",
            len(tracking),
            len(unfulfilled_orders),
        )
        return tracking

    def _get_tracking(self, customer_po: str) -> str | None:
        po_lookup = customer_po[1:] if customer_po and customer_po[0].isalpha() else customer_po
        if not self.fishbowl.isSO(po_lookup):
            return None
        po_num = self.fishbowl.getPONum(po_lookup)
        if po_num:
            tracking_numbers = get_tracking_from_outlook(po_num, self.outlook)
            if len(tracking_numbers) == 1:
                return list(tracking_numbers.values())[0][0]
        else:
            tracking_numbers = self.fishbowl.getTracking(po_lookup)
            if tracking_numbers:
                return tracking_numbers[0]
        return None

    def _process_tracking_updates(self, tracking_map: dict[str, str]):
        zero_cost_pos: list[str] = []
        added_tracking: list[str] = []
        for customer_po, tracking_number in tracking_map.items():
            po_num = (
                self.fishbowl.getPONum(customer_po[0])
                if customer_po and customer_po[0].isalpha()
                else self.fishbowl.getPONum(customer_po)
            )
            carrier = self.magento.getCarrier(tracking_number)
            status, received_date = self._check_tracking_status(
                tracking_number, carrier, customer_po
            )
            if self._is_recent_valid_tracking(status, received_date):
                self._add_tracking_number_and_fulfill(
                    customer_po, tracking_number, po_num, zero_cost_pos
                )
                added_tracking.append(customer_po)

        if zero_cost_pos:
            self.outlook.sendMail(
                "sales@factorywheelwarehouse.com",
                "Unfulfilled POs with Tracking Received",
                "The following POs have had tracking uploaded but had zero cost "
                f"PO items:\n\n{zero_cost_pos}",
            )

        self.logger.info(
            "Tracking completed successfully with %s tracking numbers uploaded",
            added_tracking,
        )

    def _check_tracking_status(
            self, tracking_number: str, carrier: str, customer_po: str
    ) -> tuple[str, datetime]:
        tracking_data = self.tracking_checker.get_tracking_details(tracking_number, carrier)
        if self.tracking_checker.status_code == 200:
            status = tracking_data["data"][0]["status"]
            origin_info = tracking_data["data"][0].get("origin_info")
            if origin_info and origin_info.get("ItemReceived"):
                received_date = datetime.strptime(
                    origin_info["ItemReceived"],
                    "%Y-%m-%d %H:%M:%S",
                )
            else:
                received_date = datetime.now()
            return status, received_date
        self.tracking_checker.add_single_tracking(tracking_number, carrier, customer_po)
        return self._check_tracking_status(tracking_number, carrier, customer_po)

    @staticmethod
    def _is_recent_valid_tracking(status: str, received_date: datetime) -> bool:
        status_is_valid = status not in ["expired", "notfound"]
        lookback_window = datetime.today() - timedelta(days=30)
        received_date_is_valid = received_date >= lookback_window
        return status_is_valid and received_date_is_valid

    def _add_tracking_number_and_fulfill(
            self,
            customer_po: str,
            tracking_number: str,
            po_num: str | None,
            zero_cost_pos: list[str],
    ):
        self.magento.addOrderTracking(customer_po, tracking_number)
        reference_customer_po = customer_po[1:] if customer_po and customer_po[0].isalpha() else customer_po
        if self.processed_order_dao.get_item(reference_customer_po):
            self.processed_order_dao.mark_order_shipped(reference_customer_po)
        # Legacy behavior regarding Fishbowl fulfillment / zero-cost POs is retained but
        # still disabled (see original implementation). zero_cost_pos is preserved in case
        # future logic reintroduces that workflow.
