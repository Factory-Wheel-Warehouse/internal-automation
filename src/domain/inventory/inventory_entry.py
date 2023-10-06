from dataclasses import dataclass

from src.domain.inventory.vendor_availability import VendorAvailability


@dataclass
class InventoryEntry:
    sku: str
    finish_status: str
    availability: list[VendorAvailability]
