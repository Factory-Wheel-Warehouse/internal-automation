from dataclasses import dataclass


@dataclass
class ClassificationConfig:
    classification_condition_column: int
    core_condition: str | None = None
    finish_condition: str | None = None
