from typing import Type

from src.dao.dao import DAO
from src.dao.dao import T
from src.domain.vendor import VendorConfig
from src.util.aws.dynamodb.constants import VENDOR_CONFIG_TABLE


class VendorConfigDAO(DAO):
    @property
    def table_name(self):
        return VENDOR_CONFIG_TABLE

    @property
    def _partition_key(self) -> str:
        return "vendor_name"

    @property
    def _dataclass(self) -> Type[T]:
        return VendorConfig
