from datetime import date
from dataclasses import dataclass

from internalprocesses.orders.address import Address


@dataclass
class Order:
    address: Address
    customer_po: str
    hollander: str
    qty: int
    price: float
    platform: str
    account: str
    vendor: str = None
    soNum: str = None
    poNum: str | None = None
    cost: float = 0.0
    status: str | None = None
    processed_date: str = str(date.today())
    ship_by_date: str | None = None
    shipped: bool = False
    date_shipped: str | None = None

    def __str__(self):
        if self.poNum:
            string = f"{self.hollander} x{self.qty} PO #{self.poNum}\n\n"
        else:
            string = f"{self.hollander} x{self.qty} SO #{self.soNum}\n\n"
        string += f"{self.address}"
        return string
