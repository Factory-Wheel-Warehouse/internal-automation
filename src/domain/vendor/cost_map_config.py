from dataclasses import dataclass

from src.domain.vendor.map_config import MapConfig


@dataclass
class CostMapConfig(MapConfig):
    part_number_column: int = 0
    cost_column: int = 1
    file_path: str = None
    dir_path: str = None

    def __post_init__(self):
        self.key_column = self.part_number_column
        self.value_column = self.cost_column
