from dataclasses import dataclass


@dataclass
class HandlingTime:
    ebay: int
    amazon: int
    walmart: int


@dataclass
class VendorAvailability:
    quantity: int
    cost: float
    handling_time: HandlingTime


@dataclass
class PartAvailability:
    vendor_name: str
    vendor_availability: VendorAvailability


@dataclass
class Part:
    part_number: str
    handling_times: HandlingTime

# @dataclass
# class Part:
#     part_number: str
#     availability: PartAvailability
