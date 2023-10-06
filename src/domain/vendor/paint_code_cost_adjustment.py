from dataclasses import dataclass
from dataclasses import field

from src.domain.generic import DefaultMap


@dataclass
class PaintCodeCostAdjustment(DefaultMap):
    default: float = 0.0
    ucodes: dict = field(default_factory=dict)

    @property
    def _map(self) -> dict[str, any] | None:
        return self.ucodes
