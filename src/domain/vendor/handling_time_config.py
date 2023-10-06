from dataclasses import dataclass

from src.domain.vendor.handling_time_map import HandlingTimeMap


@dataclass
class HandlingTimeConfig:
    core_handling_times: HandlingTimeMap
    finished_handling_times: HandlingTimeMap

    def get(self, ucode: str, status: str):  # Change to WheelStatusType
        if status == "CORE":
            return self.core_handling_times.get(ucode)
        return self.finished_handling_times.get(ucode)
