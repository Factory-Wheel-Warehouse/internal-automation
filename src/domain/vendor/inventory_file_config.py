from dataclasses import dataclass


@dataclass
class InventoryFileConfig:
    part_number_column: int
    quantity_column: int
    quantity_deduction: int | None = None
    file_path: str | None = None
    dir_path: str | None = None
    cost_column: int | None = None
    encoding: str = "utf-8"

    def __post_init__(self):
        if (not (self.file_path or self.dir_path) or
                (self.file_path and self.dir_path)):
            raise Exception("InventoryFileConfig must have only one of either "
                            "file_path or dir_path defined")
