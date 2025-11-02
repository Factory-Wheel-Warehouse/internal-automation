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
        self.logger.info("Starting tracking update run")
        self.outlook.login()
        self.fishbowl.start()
        try:
            unfulfilled_orders = self.magento.get_pending_orders()
            self.logger.info("Retrieved %s unfulfilled orders", len(unfulfilled_orders))
            tracking_candidates = self._collect_tracking_candidates(unfulfilled_orders)
            self._process_tracking_updates(tracking_candidates)
        finally:
            self.fishbowl.close()
            self.logger.info("Tracking update run complete")

    # --- internal helpers -------------------------------------------------

    def _collect_tracking_candidates(self, unfulfilled_orders: list[str]) -> dict[str, dict]:
        tracking = {}
        for customer_po in unfulfilled_orders:
            if self.magento.isWalmartOrder(customer_po):
                self.logger.debug("Skipping Walmart order %s", customer_po)
                continue
            tracking_info = self._get_tracking(customer_po)
            if tracking_info:
                tracking[customer_po] = tracking_info
            else:
                self.logger.debug("No tracking located for %s", customer_po)
        self.logger.info(
            "Found tracking numbers for %s of %s orders",
            len(tracking),
            len(unfulfilled_orders),
        )
        return tracking

    def _get_tracking(self, customer_po: str) -> dict | None:
        identifier = customer_po[1:] if customer_po and customer_po[0].isalpha() else customer_po
        if not self.fishbowl.isSO(identifier):
            return None
        po_num = self.fishbowl.getPONum(identifier)
        if po_num:
            tracking_numbers = get_tracking_from_outlook(po_num, self.outlook)
            for carrier, numbers in tracking_numbers.items():
                if numbers:
                    self.logger.debug(
                        "Using Outlook tracking %s (%s) for %s",
                        numbers[0], carrier, customer_po
                    )
                    return {"number": numbers[0], "carrier": carrier.lower()}
        tracking_numbers = self.fishbowl.getTracking(identifier)
        if tracking_numbers:
            number = tracking_numbers[0]
            carrier = self.magento.getCarrier(number)
            self.logger.debug(
                "Falling back to Fishbowl tracking %s (%s) for %s",
                number, carrier, customer_po
            )
            return {"number": number, "carrier": carrier}
        return None

    def _process_tracking_updates(self, tracking_map: dict[str, dict]):
        zero_cost_pos: list[str] = []
        added_tracking: list[str] = []
        for customer_po, tracking_info in tracking_map.items():
            tracking_number = tracking_info["number"]
            carrier = tracking_info.get("carrier") or self.magento.getCarrier(tracking_number)
            po_num = (
                self.fishbowl.getPONum(customer_po[1:])
                if customer_po and customer_po[0].isalpha()
                else self.fishbowl.getPONum(customer_po)
            )
            status, received_date = self._check_tracking_status(
                tracking_number, carrier, customer_po
            )
            if self._is_recent_valid_tracking(status, received_date):
                self._add_tracking_number_and_fulfill(
                    customer_po, tracking_number, po_num, zero_cost_pos
                )
                added_tracking.append(customer_po)
                self.logger.info(
                    "Uploaded tracking %s (%s) for %s",
                    tracking_number, carrier, customer_po
                )
            else:
                self.logger.warning(
                    "Skipping tracking %s for %s due to status '%s' or stale date %s",
                    tracking_number, customer_po, status, received_date,
                )

        if not tracking_map:
            self.logger.info("No tracking candidates identified")

        if zero_cost_pos:
            self.outlook.sendMail(
                "sales@factorywheelwarehouse.com",
                "Unfulfilled POs with Tracking Received",
                "The following POs have had tracking uploaded but had zero cost "
                f"PO items:\n\n{zero_cost_pos}",
            )
            self.logger.warning("POs with zero cost encountered: %s", zero_cost_pos)

        self.logger.info(
            "Tracking completed successfully with %s tracking numbers uploaded",
            added_tracking,
        )

    def _check_tracking_status(
            self, tracking_number: str, carrier: str, customer_po: str
    ) -> tuple[str, datetime]:
        tracking_data = self.tracking_checker.get_tracking_details(tracking_number, carrier)
        if self.tracking_checker.status_code == 200 and tracking_data:
            tracking_entries = tracking_data.get("data") or []
            if tracking_entries:
                origin_info = tracking_entries[0].get("origin_info")
                status = tracking_entries[0]["status"]
                if origin_info and origin_info.get("ItemReceived"):
                    received_date = datetime.strptime(
                        origin_info["ItemReceived"],
                        "%Y-%m-%d %H:%M:%S",
                    )
                else:
                    received_date = datetime.now()
                return status, received_date
            self.logger.warning(
                "Tracktry responded with status 200 but no tracking data for %s",
                tracking_number,
            )
            return "notfound", datetime.now()
        if self.tracking_checker.status_code != 200:
            self.tracking_checker.add_single_tracking(tracking_number, carrier, customer_po)
            return self._check_tracking_status(tracking_number, carrier, customer_po)
        self.logger.warning(
            "Unable to parse Tracktry response for %s (status %s)",
            tracking_number,
            self.tracking_checker.status_code,
        )
        return "notfound", datetime.now()

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
