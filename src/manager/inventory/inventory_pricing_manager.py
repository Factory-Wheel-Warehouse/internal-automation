from src.dao.vendor_config_dao import VendorConfigDAO
from src.domain.vendor import VendorConfig
from src.manager.manager import Manager
from src.util.constants.credentials import FTP_CREDENTIALS
from src.facade.ftp.ftp_facade import FTPFacade
from src.util.constants.inventory import COAST_PRICING_SHEET
from src.util.constants.inventory import DOLLAR_ROUND_DIGITS
from src.util.constants.inventory import HIGH_COST_MARGIN
from src.util.constants.inventory import HIGH_COST_THRESHOLD
from src.util.constants.inventory import LOW_COST_MARGIN
from src.util.constants.inventory import MASTER_PRICING_MAP
from src.util.inventory import get_adjusted_cost
from src.util.inventory.pricing_util import get_list_price
from src.util.inventory.pricing_util import get_sku_map
from src.util.inventory.pricing_util import get_stats

HEADERS = ["sku", "total_qty", "final_magento_qty", "avg_ht",
           "walmart_ht", "list_price"]
VENDOR_SPECIFIC_HEADERS = ["cost", "fin_qty", "core_qty", "combined_qty", "ht"]


class InventoryManager(Manager):
    _ftp: FTPFacade | None = None
    _coast_vendor_config: VendorConfig | None = None

    def _set_attrs(self):
        self._ftp = FTPFacade(**FTP_CREDENTIALS)
        self._coast_vendor_config = VendorConfigDAO().get_item("Coast To "
                                                               "Coast")

    @Manager.action
    def upload(self):
        return "Upload combined master inventory"

    @Manager.action
    def email(self):
        return "Email combined master inventory"

    @Manager.action
    def pricing(self):
        self._set_attrs()
        prices = []
        map_ = get_sku_map(self._ftp, self._coast_vendor_config)
        rows = self._ftp.get_file_as_list(COAST_PRICING_SHEET)
        for row in rows:
            part_num, base_cost = row
            sku = map_.get(part_num)
            if sku:
                pricing = get_list_price(self._coast_vendor_config,
                                         sku, base_cost)
                prices.append(pricing)
        self._ftp.write_list_as_csv(MASTER_PRICING_MAP, prices)
        get_stats(sorted(prices, key=lambda x: x[1]))
