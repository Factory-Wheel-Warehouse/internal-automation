from attr import dataclass
from flask import request

from src.action.action import Action
from src.dao import VendorConfigDAO
from src.facade.ftp.ftp_facade import FTPFacade
from src.util.constants.inventory import COAST_PRICING_PATH
from src.util.constants.inventory import MASTER_PRICING_PATH
from src.util.inventory.inventory_util import get_adjusted_cost
from src.util.inventory.pricing_util import get_list_price
from src.util.inventory.pricing_util import get_sku_map


@dataclass
class PricingAction(Action):
    ftp: FTPFacade = None
    vendor_config_dao: VendorConfigDAO = VendorConfigDAO()

    def run(self, request_: request):
        self.ftp.start()
        coast_vendor_config = self.vendor_config_dao.get_item("Coast To "
                                                              "Coast")
        cost_adjustment_config = coast_vendor_config.cost_adjustment_config
        prices = []
        map_ = get_sku_map(self.ftp, coast_vendor_config)
        rows = self.ftp.get_file_as_list(COAST_PRICING_PATH)
        for row in rows:
            part_num, base_cost = row
            sku = map_.get(part_num)
            adjusted_cost = get_adjusted_cost(sku,
                                              base_cost,
                                              cost_adjustment_config)
            if sku:
                cost_adjustment = adjusted_cost - base_cost
                pricing = get_list_price(sku, base_cost, cost_adjustment)
                prices.append(pricing)
        self.ftp.write_list_as_csv(MASTER_PRICING_PATH, prices)
        self.ftp.close()
