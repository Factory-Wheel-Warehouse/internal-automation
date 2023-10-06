from dataclasses import dataclass
from dataclasses import field

from src.domain.generic import DefaultMap


@dataclass
class HandlingTimeMap(DefaultMap):
    default: int
    ucode_map: dict = field(default_factory=dict)

    @property
    def _map(self) -> dict[str, any] | None:
        return self.ucode_map
