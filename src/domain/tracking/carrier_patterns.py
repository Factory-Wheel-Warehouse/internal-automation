from src.domain.generic import IterableEnum


class CarrierPatterns(IterableEnum):
    FEDEX: str = r"\d{12}"
    UPS: str = r"1Z\w{8}\d{8}"
