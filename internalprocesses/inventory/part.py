from dataclasses import dataclass

from internalprocesses.inventory.constants import MATERIAL_CODE_END, \
    PAINT_CODE_START


@dataclass
class Sku:
    sku: str

    def __post_init__(self):
        self.material = self.sku[:MATERIAL_CODE_END]
        self.hollander = self.sku[MATERIAL_CODE_END: PAINT_CODE_START]
        self.ucode = self.sku[PAINT_CODE_START:]
        self.core = self.sku[:PAINT_CODE_START]


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
    sku: str
    handling_times: HandlingTime

# @dataclass
# class Part:
#     part_number: str
#     availability: PartAvailability
