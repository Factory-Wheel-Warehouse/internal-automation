from dataclasses import dataclass

from src.domain.vendor.map_config import MapConfig


@dataclass
class SkuMapConfig(MapConfig):
    inhouse_part_number_column: int = 0
    vendor_part_number_column: int = 1
    file_path: str = None
    dir_path: str = None

    def __post_init__(self):
        self.key_column = self.vendor_part_number_column
        self.value_column = self.inhouse_part_number_column
