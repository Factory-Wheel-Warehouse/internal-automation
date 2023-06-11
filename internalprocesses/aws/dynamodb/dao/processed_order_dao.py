from typing import Type

from internalprocesses.aws.dynamodb.dao.dao import DAO, T
from internalprocesses.orders.orders import Order


class ProcessedOrderDAO(DAO):

    @property
    def _partition_key(self) -> str:
        return "customer_po"

    @property
    def table_name(self) -> str:
        return "internal_automation_processed_order"

    @property
    def _dataclass(self) -> Type[T]:
        return Order
