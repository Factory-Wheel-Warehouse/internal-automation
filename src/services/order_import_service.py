import json
import logging
import os
import re
from collections import defaultdict
from datetime import date, timedelta

from dotenv import load_dotenv

from src.dao.processed_order_dao import ProcessedOrderDAO
from src.dao.vendor_config_dao import VendorConfigDAO
from src.domain.fishbowl.sales_order_item_type import SalesOrderItemType
from src.domain.inventory.inventory import Inventory
from src.domain.order.address import Address
from src.domain.order.order import Order
from src.facade.fishbowl import FishbowlFacade
from src.facade.ftp.ftp_facade import FTPFacade
from src.facade.magento.magento_facade import Environment, MagentoFacade
from src.facade.outlook import OutlookFacade
from src.util.constants.inventory import PAINT_CODE_START
from src.util.constants.order import CHANNEL_FEE, WALMART_FEE
from src.util.order.magento_parsing_utils import get_channel_fee


class OrderImportService:
    """Handles Magento order ingestion and Fishbowl import orchestration."""

    def __init__(
            self,
            env: Environment = Environment.PROD,
            magento: MagentoFacade | None = None,
            fishbowl: FishbowlFacade | None = None,
            ftp: FTPFacade | None = None,
            outlook: OutlookFacade | None = None,
            vendor_config_dao: VendorConfigDAO | None = None,
            processed_order_dao: ProcessedOrderDAO | None = None,
            inventory: Inventory | None = None,
            config: dict | None = None,
            config_path: str | None = None,
            logger: logging.Logger | None = None,
    ):
        load_dotenv()
        self.logger = logger or logging.getLogger(__name__)
        self.magento = magento or MagentoFacade(env)
        self.fishbowl = fishbowl or FishbowlFacade()
        self.ftp = ftp or FTPFacade()
        self.outlook = outlook or OutlookFacade()
        self.vendor_config_dao = vendor_config_dao or VendorConfigDAO()
        self.processed_order_dao = processed_order_dao or ProcessedOrderDAO()
        self.inventory = inventory or Inventory()
        self.config = config or self._read_config(config_path)
        self.customers = self.config["Main Settings"]["Customers"]
        self.vendors = {v.vendor_name: v for v in self.vendor_config_dao.get_all_items()}
        self.orders_by_vendor: dict[str, list[Order]] = defaultdict(list)
        self.exception_orders: list[str] = []
        self._resources_started = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def prepare_orders(self):
        """Load pending Magento orders, build inventory, and classify vendors."""
        self._ensure_resources()
        self.orders_by_vendor = defaultdict(list)
        self.exception_orders = []
        self.inventory.build(self.ftp, self.fishbowl)
        for order_id in self.magento.get_pending_orders():
            order_details = self.magento.get_order_details(order_id)
            address = self._get_magento_address(order_details)
            order = self._build_magento_order(order_details, order_id, address)
            if order and not self.fishbowl.isSO(order.customer_po):
                self._sort_order(order)

    def import_orders(self, test: bool = False):
        for vendor, orders in self.orders_by_vendor.items():
            for order in orders:
                if not self.fishbowl.isProduct(order.hollander):
                    self.fishbowl.importProduct(order.hollander)
                customer = self.customers[order.account]
                so_data = self._build_so_data(customer, order, vendor)
                if not test:
                    self._persist_sales_order(vendor, order, so_data)
        if not test:
            processed_orders = []
            for vendor, orders in self.orders_by_vendor.items():
                for order in orders:
                    order.soNum = self.fishbowl.getSONum(order.customer_po)
                    if self.vendors.get(vendor) or vendor == "No Vendor":
                        order.poNum = self.fishbowl.getPONum(order.customer_po)
                    ship_by = self._get_ship_by_date(order)
                    if ship_by:
                        order.ship_by_date = ship_by
                    processed_orders.append(order)
            if processed_orders:
                self.processed_order_dao.batch_write_items(processed_orders)

    def send_vendor_notifications(self, email_address: str):
        for vendor, orders in self.orders_by_vendor.items():
            if orders:
                self._email_dropships(orders, vendor, email_address)

    def send_exception_notifications(self, email_address: str):
        if self.exception_orders:
            body = "".join(self.exception_orders)
            self.outlook.sendMail(email_address, "Multiline/Exception Orders", body)

    def close(self):
        if self._resources_started:
            self.fishbowl.close()
            self.ftp.close()
            self._resources_started = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_config(config_path: str | None) -> dict:
        if not config_path:
            current_dir = os.path.dirname(__file__)
            config_path = os.path.join(current_dir, "..", "..", "data", "config.json")
        with open(os.path.abspath(config_path)) as fh:
            return json.load(fh)

    def _ensure_resources(self):
        if not self._resources_started:
            self.fishbowl.start()
            self.ftp.start()
            self.outlook.login()
            self._resources_started = True

    def _persist_sales_order(self, vendor: str, order: Order, so_data: list[str]):
        if vendor in self.vendors:
            self.fishbowl.adjust_vendor_part_cost(order.hollander, vendor, order.cost)
        elif vendor == "No Vendor":
            self.fishbowl.importPPVP(order.hollander)
        self.fishbowl.importSalesOrder(so_data)

    def _get_magento_address(self, order_details: dict) -> Address:
        shipping = order_details["extension_attributes"]["shipping_assignments"][0]["shipping"]["address"]
        shipping.setdefault("firstname", "")
        shipping.setdefault("lastname", "")
        address = Address(
            " ".join([shipping["firstname"] or "", shipping["lastname"] or ""]).strip(),
            shipping["street"][0],
            shipping["city"], shipping["region_code"],
            shipping["postcode"],
        )
        if len(shipping["street"]) > 1:
            address.street2 = shipping["street"][1]
        return address

    def _build_magento_order(self, order_details: dict, order_id: str, address: Address) -> Order | None:
        line_items = order_details.get("items", [])
        if not line_items or len(line_items) != 1:
            return self._record_exception(order_id)
        item = line_items[0]
        sku = self._check_for_valid_sku(item["sku"]) or self._check_for_valid_sku(item["name"])
        if not sku:
            return self._record_exception(order_id)
        if self.magento.isEbayOrder(order_id):
            account = self.magento.getEbayAccount(order_id)
            order_id = order_id[1:]
        else:
            account = self.magento.get_platform(order_id)
        order = Order(
            address=address,
            customer_po=order_id,
            hollander=sku,
            qty=int(item["qty_ordered"]),
            price=float(item["price"]),
            platform=self.magento.get_platform(order_id),
            account=account,
            channel_fee=get_channel_fee(order_details),
        )
        return order

    def _record_exception(self, order_id: str):
        if not self.fishbowl.isSO(order_id):
            self.exception_orders.append(f"Order #{order_id}\n\n")
        return None

    @staticmethod
    def _check_for_valid_sku(sku: str | None) -> str | None:
        if not sku:
            return None
        pattern = r"(ALY|STL)[0-9]{5}[A-Z]{1}[0-9]{2}[N]?"
        search = re.search(pattern, sku.upper())
        if search:
            return search.group()
        return None

    def _build_so_data(self, customer: dict, order: Order, vendor: str) -> list[str]:
        channel_fee_line = (
            self._get_walmart_discount_percent_line()
            if not order.channel_fee and order.account == "walmart"
            else self._get_channel_fee_so_line(order.channel_fee)
        )
        return [
            self._build_so_string(customer, order),
            self._build_so_item_string(order, vendor),
            channel_fee_line,
        ]

    def _build_so_string(self, customer: dict, order: Order) -> str:
        string = f'"SO", , 20, "{customer["Name"]}", "{customer["Name"]}", '
        string += f'"{customer["Name"]}", "{customer["Address"]}", '
        string += f'"{customer["City"]}", "{customer["State"]}", '
        string += f'"{customer["Zipcode"]}", "{customer["Country"]}", '
        string += rf'"{order.address.name}", "{order.address.street}", '
        string += f'"{order.address.city}", "{order.address.state}", '
        string += f'"{order.address.zipcode}", "United States", "false", '
        string += f'"UPS", "None", 30, "{order.customer_po}"'
        return string

    def _build_so_item_string(self, order: Order, vendor: str) -> str:
        item_type = SalesOrderItemType.SALE if vendor == "Warehouse" else SalesOrderItemType.DROP_SHIP
        return (
            f'"Item", {item_type}, "{order.hollander}", , {order.qty}, '
            f'"ea", {order.price}, , , , , , , , , '
        )

    @staticmethod
    def _get_channel_fee_so_line(channel_fee: float) -> str:
        return (
            f'"Item", {SalesOrderItemType.DISCOUNT_AMOUNT}, "{CHANNEL_FEE}", '
            f', , , {-1 * channel_fee}, , , , , , , , , '
        )

    @staticmethod
    def _get_walmart_discount_percent_line() -> str:
        return (
            f'"Item", {SalesOrderItemType.DISCOUNT_PERCENTAGE}, "{WALMART_FEE}", '
            ", , , , , , , , , , , , "
        )

    def _sort_order(self, order: Order):
        vendor, order.cost, order.status = self.inventory.get_cheapest_vendor(order.hollander, order.qty)
        order.vendor = vendor
        self.orders_by_vendor[vendor].append(order)

    def _get_ship_by_date(self, order: Order):
        vendor = self.vendors.get(order.vendor)
        if vendor and vendor.handling_time_config:
            ucode = order.hollander[PAINT_CODE_START:]
            status = order.status
            ht = vendor.handling_time_config.get(ucode, status)
            return str(date.today() + timedelta(days=ht))
        return None

    def _email_dropships(self, orders, vendor, email_address):
        email_body = ""
        for index, order in enumerate(orders):
            if index > 0:
                email_body += "\n\n"
            email_body += str(order)
            if index < len(orders) - 1:
                email_body += "\n\n" + ("-" * 44)
        self.outlook.sendMail(email_address, f"{vendor} Orders", email_body)
