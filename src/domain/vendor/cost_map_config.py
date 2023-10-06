from dataclasses import dataclass

from src.domain.vendor.map_config import MapConfig


@dataclass
class CostMapConfig(MapConfig):
    part_number_column: int = 0
    cost_column: int = 1
    file_path: str = None
    dir_path: str = None

    @property
    def key_column(self):
        return self.part_number_column

    @property
    def value_column(self):
        return self.cost_column
