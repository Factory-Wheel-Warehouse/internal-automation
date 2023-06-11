from typing import Type

from internalprocesses.aws.dynamodb.constants import VENDOR_CONFIG_TABLE
from internalprocesses.aws.dynamodb.dao.dao import DAO, T
from internalprocesses.vendor import VendorConfig


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
