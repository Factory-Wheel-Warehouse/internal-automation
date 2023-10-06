from dataclasses import dataclass

from src.domain.generic import DefaultMap


@dataclass
class HandlingTimeMap(DefaultMap):  # TODO: Implement abstract DefaultMap?

    default: int
    ucode_map: dict | None = None

    @property
    def _map(self) -> dict[str, any] | None:
        return self.ucode_map
