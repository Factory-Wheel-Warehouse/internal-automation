from typing import Type

from internalprocesses.aws.dynamodb.constants import COMPARISON_OPERATOR_KEY, \
    EQUAL_TO, ATTRIBUTE_VALUE_LIST_KEY
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

    def get_orders_by_sbd(self, ship_by_date: str) -> list[Order]:
        attribute_key = "ship_by_date"
        return self.get_all_items(ship_by_date={
            ATTRIBUTE_VALUE_LIST_KEY: [self._marshall({
                attribute_key: ship_by_date
            }).get(attribute_key)],
            COMPARISON_OPERATOR_KEY: EQUAL_TO
        })
