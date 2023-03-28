import traceback
from dataclasses import dataclass

from internalprocesses.orders.address import Address


@dataclass
class VendorConfig:
    def __init__(self, vendor_name: str, address: dict,
                 inventory_file_config: dict, cost_adjustment_config: dict =
                 None, sku_map_config: dict = None, cost_map_config: dict =
                 None, classification_config: dict = None,
                 inclusion_config: dict = None) -> None:
        cost_column = inventory_file_config.get("cost_column")
        if (
                not cost_map_config and cost_column is None
        ) or (
                cost_map_config and cost_column is not None
        ):
            print(cost_map_config, inventory_file_config.get("cost_column"))
            raise Exception(f"{vendor_name} must have only one of either " +
                            "file_path.cost_column or cost_map_config defined",
                            traceback.print_exc())
        self.vendor_name = vendor_name
        self.address = Address(**address)
        self.inventory_file_config = InventoryFileConfig(
            **inventory_file_config)
        if cost_adjustment_config:
            self.cost_adjustment_config = CostConfig(**cost_adjustment_config)
        else:
            self.cost_adjustment_config = CostConfig()
        if sku_map_config:
            self.sku_map_config = SkuMapConfig(**sku_map_config)
        if cost_map_config:
            self.cost_map_config = CostMapConfig(**cost_map_config)
        if classification_config:
            self.classification_config = ClassificationConfig(
                **classification_config)
        else:
            self.classification_config = ClassificationConfig()
        if inclusion_config:
            self.inclusion_config = InclusionConfig(**inclusion_config)
        else:
            self.inclusion_config = InclusionConfig()


class CostConfig:
    def __init__(self, steel_adjustment: int = 0, alloy_adjustment: int = 0,
                 general_adjustment: int = 0) -> None:
        self.steel_adjustment = steel_adjustment
        self.alloy_adjustment = alloy_adjustment
        self.general_adjustment = general_adjustment


class InventoryFileConfig:
    def __init__(self, part_number_column: int, quantity_column: int,
                 cost_column: int = None, file_path: str = None,
                 dir_path: str = None) -> None:
        if not (file_path or dir_path) or (file_path and dir_path):
            raise Exception("InventoryFileConfig must have only one of either "
                            "file_path or dir_path defined")
        self.file_path = file_path
        self.dir_path = dir_path
        self.part_number_column = part_number_column
        self.cost_column = cost_column
        self.quantity_column = quantity_column


class MapConfig:
    def __init__(self, file_path: str = None, dir_path: str = None,
                 key_column: int = None, value_column: int = None):
        if not (file_path or dir_path) or (file_path and dir_path):
            raise Exception("MapConfig must have only one of either file_path "
                            "or dir_path defined", traceback.print_exc())
        self.file_path = file_path
        self.dir_path = dir_path
        self.key_column = key_column
        self.value_column = value_column


class SkuMapConfig(MapConfig):
    def __init__(self, file_path: str = None, dir_path: str = None,
                 inhouse_part_number_column: int = 0,
                 vendor_part_number_column=1) -> None:
        super().__init__(file_path, dir_path, vendor_part_number_column,
                         inhouse_part_number_column)


class CostMapConfig(MapConfig):
    def __init__(self, file_path: str = None, dir_path: str = None,
                 part_number_column: int = None,
                 cost_column: int = None) -> None:
        super().__init__(file_path, dir_path, part_number_column, cost_column)


class ClassificationConfig:
    def __init__(self, core_condition: str = None,
                 finish_condition: str = None,
                 classification_condition_column: int = None) -> None:
        self.core_condition = core_condition
        self.finish_condition = finish_condition
        self.classification_condition_column = classification_condition_column


class InclusionConfig:
    def __init__(self, inclusion_condition: str = None,
                 exclusion_condition: str = None,
                 inclusion_condition_column: int = None) -> None:
        self.inclusion_condition = inclusion_condition
        self.exclusion_condition = exclusion_condition
        self.inclusion_condition_column = inclusion_condition_column
