from dataclasses import dataclass

from src.domain.vendor.paint_code_cost_adjustment import \
    PaintCodeCostAdjustment


@dataclass
class CostConfig:
    steel_adjustment: float = 0.0
    alloy_adjustment: float = 0.0
    general_adjustment: float = 0.0
    ucode_adjustment: PaintCodeCostAdjustment | None = None
