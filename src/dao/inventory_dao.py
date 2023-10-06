from typing import Type

from src.dao.dao import DAO
from src.dao.dao import T
from src.domain.inventory.inventory_entry import InventoryEntry
from src.util.aws.dynamodb.constants import INVENTORY_TABLE
from src.util.aws.dynamodb.table_config import AttributeDefinition
from src.util.aws.dynamodb.table_config import KeySchema
from src.util.aws.dynamodb.table_config import TableConfig


class InventoryDAO(DAO):
    @property
    def table_name(self) -> str:
        return INVENTORY_TABLE

    @property
    def _partition_key(self) -> str:
        return "sku"

    @property
    def _sort_key(self) -> str:
        return "finish_status"

    @property
    def _dataclass(self) -> Type[T]:
        return InventoryEntry

    @property
    def _table_config(self) -> TableConfig | None:
        return TableConfig(
            [AttributeDefinition(self._partition_key, "S"),
             AttributeDefinition(self._sort_key, "S")],
            self.table_name,
            [KeySchema(self._partition_key, "HASH"),
             KeySchema(self._sort_key, "RANGE")]
        )
