import traceback
from abc import ABC
from dataclasses import dataclass

from internalprocesses.orders.address import Address


@dataclass
class CostConfig:
    steel_adjustment: float = 0.0
    alloy_adjustment: float = 0.0
    general_adjustment: float = 0.0


@dataclass
class InventoryFileConfig:
    part_number_column: int
    quantity_column: int
    file_path: str | None = None
    dir_path: str | None = None
    cost_column: int | None = None

    def __post_init__(self):
        if (not (self.file_path or self.dir_path) or
                (self.file_path and self.dir_path)):
            raise Exception("InventoryFileConfig must have only one of either "
                            "file_path or dir_path defined")


@dataclass
class MapConfig(ABC):
    file_path: str | None = None
    dir_path: str | None = None
    key_column: int = None
    value_column: int = None

    def __post_init__(self):
        if (not (self.file_path or self.dir_path) or
                (self.file_path and self.dir_path)):
            raise Exception("MapConfig must have only one of either file_path "
                            "or dir_path defined", traceback.print_exc())


@dataclass
class SkuMapConfig(MapConfig):
    inhouse_part_number_column: int = 0
    vendor_part_number_column: int = 1
    file_path: str = None
    dir_path: str = None

    def __post_init__(self):
        self.key_column = self.vendor_part_number_column
        self.value_column = self.inhouse_part_number_column


@dataclass
class CostMapConfig(MapConfig):
    part_number_column: int = 0
    cost_column: int = 1
    file_path: str = None
    dir_path: str = None

    def __post_init__(self):
        self.key_column = self.part_number_column
        self.value_column = self.cost_column


@dataclass
class ClassificationConfig:
    classification_condition_column: int
    core_condition: str | None = None
    finish_condition: str | None = None


@dataclass
class InclusionConfig:
    inclusion_condition_column: int
    inclusion_condition: str | None = None
    exclusion_condition: str | None = None


@dataclass
class VendorConfig:
    vendor_name: str
    address: Address
    inventory_file_config: InventoryFileConfig
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
