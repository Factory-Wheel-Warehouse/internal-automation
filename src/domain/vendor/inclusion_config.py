from dataclasses import dataclass


@dataclass
class InclusionConfig:
    inclusion_condition_column: int
    inclusion_condition: str | None = None
    exclusion_condition: str | None = None
