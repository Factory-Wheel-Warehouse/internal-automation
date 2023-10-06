from dataclasses import dataclass


@dataclass
class VendorAvailability:
    vendor_name: str
    quantity: int
    cost: float
    handling_time: int
