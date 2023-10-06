from dataclasses import dataclass

from src.domain.generic import DefaultMap


@dataclass
class PaintCodeCostAdjustment(DefaultMap):
    default: float = 0.0
    ucodes: dict | None = None

    @property
    def _map(self) -> dict[str, any] | None:
        return self.ucodes
