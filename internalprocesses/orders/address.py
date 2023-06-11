from dataclasses import dataclass


@dataclass
class Address:
    name: str
    street1: str
    city: str
    state: str
    zipcode: str
    country: str = "UNITED STATES"
    street2: str | None = None

    def __post_init__(self):
        self.street = self.street1

    def __str__(self):
        outp = f"{self.name}\n{self.street}\n"
        outp += f"{self.city} {self.state} {self.zipcode}"
        return outp
