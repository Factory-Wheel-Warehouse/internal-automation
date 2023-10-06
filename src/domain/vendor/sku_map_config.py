from dataclasses import dataclass

from src.domain.vendor.map_config import MapConfig


@dataclass
class SkuMapConfig(MapConfig):
    inhouse_part_number_column: int = 0
    vendor_part_number_column: int = 1
    file_path: str = None
    dir_path: str = None

    @property
    def key_column(self):
        return self.vendor_part_number_column

    @property
    def value_column(self):
        return self.inhouse_part_number_column
