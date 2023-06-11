import datetime
from dataclasses import asdict
from datetime import date
from typing import Type

from internalprocesses.aws.dynamodb.constants import INVENTORY_TABLE
from internalprocesses.aws.dynamodb.dao.dao import DAO, T
from internalprocesses.aws.dynamodb.table_config import TableConfig, \
    AttributeDefinition, KeySchema
from internalprocesses.inventory.part import Part
from internalprocesses.orders.orders import Order


class InventoryDAO(DAO):
    @property
    def table_name(self) -> str:
        return INVENTORY_TABLE

    @property
    def _partition_key(self) -> str:
        return "part_number"

    @property
    def _dataclass(self) -> Type[T]:
        return Part

    @property
    def _table_config(self) -> TableConfig | None:
        return TableConfig(
            [AttributeDefinition(self._partition_key, "S")],
            self.table_name,
            [KeySchema(self._partition_key, "HASH")]
        )

    def get_ship_by_date(self, order: Order) -> str:
        part = self.get_item(order.hollander)
        handling_times = asdict(part.handling_times)
        ht_days = handling_times.get(order.platform)
        if ht_days:
            start_date = date.fromisoformat(order.processed_date)
            return str(start_date + datetime.timedelta(days=ht_days))
