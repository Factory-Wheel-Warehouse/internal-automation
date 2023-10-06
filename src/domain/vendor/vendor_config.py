import traceback
from dataclasses import dataclass

from src.domain.order.address import Address
from src.domain.vendor.classification_config import ClassificationConfig
from src.domain.vendor.cost_config import CostConfig
from src.domain.vendor.cost_map_config import CostMapConfig
from src.domain.vendor.handling_time_config import HandlingTimeConfig
from src.domain.vendor.inclusion_config import InclusionConfig
from src.domain.vendor.inventory_file_config import InventoryFileConfig
from src.domain.vendor.sku_map_config import SkuMapConfig


@dataclass
class VendorConfig:
    vendor_name: str
    address: Address
    inventory_file_config: InventoryFileConfig
    handling_time_config: HandlingTimeConfig
    cost_adjustment_config: CostConfig | None = None
    sku_map_config: SkuMapConfig | None = None
    cost_map_config: CostMapConfig | None = None
    classification_config: ClassificationConfig | None = None
    inclusion_config: InclusionConfig | None = None

    def __post_init__(self):
        cost_column = self.inventory_file_config.cost_column
        if (
                not self.cost_map_config and cost_column is None
        ) or (
                self.cost_map_config and cost_column is not None
        ):
            raise Exception(f"{self.vendor_name} must have only one of "
                            "either file_path.cost_column or "
                            "cost_map_config defined",
                            traceback.print_exc())

    def get_handling_time(self, ucode: str, status: str):
        return self.handling_time_config.get(ucode, status)
