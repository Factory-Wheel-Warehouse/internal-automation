import re
from dataclasses import dataclass

from src.domain.tracking.carrier import Carrier
from src.domain.tracking.carrier_patterns import CarrierPatterns


@dataclass
class TrackingNumber:
    number: str

    def get_carrier(self) -> Carrier:
        for carrier, pattern in CarrierPatterns.map():
            if re.match(pattern, self.number):
                return Carrier[carrier]
