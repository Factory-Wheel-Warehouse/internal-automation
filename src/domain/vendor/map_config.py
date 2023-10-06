import traceback
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass


@dataclass
class MapConfig(ABC):
    file_path: str | None = None
    dir_path: str | None = None
    encoding: str = "utf-8"

    @property
    @abstractmethod
    def key_column(self):
        pass

    @property
    @abstractmethod
    def value_column(self):
        pass

    def __post_init__(self):
        if (not (self.file_path or self.dir_path) or
                (self.file_path and self.dir_path)):
            raise Exception("MapConfig must have only one of either file_path "
                            "or dir_path defined", traceback.print_exc())
