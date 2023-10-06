import traceback
from abc import ABC
from dataclasses import dataclass

from internalprocesses.orders.address import Address


@dataclass
class UCodeAdjustment:  # TODO: Abstract to DefaultMap Abstract class?
    default: float = 0.0
    ucodes: dict | None = None

    def get(self, ucode: str):
        if self.ucodes:
            adjustment = self.ucodes.get(ucode)
            if adjustment:
                return adjustment
        return self.default


@dataclass
class CostConfig:
    steel_adjustment: float = 0.0
    alloy_adjustment: float = 0.0
    general_adjustment: float = 0.0
    ucode_adjustment: UCodeAdjustment | None = None


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
class HandlingTimeMap:  # TODO: Implement abstract DefaultMap?
    default: int
    ucode_map: dict | None = None

    def get(self, ucode):
        if self.ucode_map:
            ht = self.ucode_map.get(ucode)
            if ht:
                return ht
        return self.default


@dataclass
class HandlingTimeConfig:
    core_handling_times: HandlingTimeMap
    finished_handling_times: HandlingTimeMap

    def get(self, ucode: str, status: str):
        if status == "CORE":
            return self.core_handling_times.get(ucode)
        return self.finished_handling_times.get(ucode)


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
