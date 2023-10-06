import dataclasses
import json
import time
from abc import ABC, abstractmethod
from typing import Type, TypeVar

import boto3
import botocore
from dacite import from_dict, Config
from dynamodb_json import json_util as dynamodb_json

from src.util.aws.dynamodb.constants import DYNAMODB_SERVICE_NAME
from src.util.aws.dynamodb.constants import ITEMS_KEY
from src.util.aws.dynamodb.constants import ITEM_COUNT_KEY
from src.util.aws.dynamodb.constants import ITEM_KEY
from src.util.aws.dynamodb.constants import NONE
from src.util.aws.dynamodb.constants import ON_DEMAND
from src.util.aws.dynamodb.constants import PUT_REQUEST_KEY
from src.util.aws.dynamodb.constants import REQUEST_ITEMS_KEY
from src.util.aws.dynamodb.constants import RETURN_CONSUMED_CAPACITY_KEY
from src.util.aws.dynamodb.constants import RETURN_ITEM_COLLECTION_METRICS_KEY
from src.util.aws.dynamodb.constants import TABLE_KEY
from src.util.aws.dynamodb.constants import TABLE_STATUS_KEY
from src.util.aws.dynamodb.dynamodb_status import DynamoDBStatus
from src.util.aws.dynamodb.table_config import TableConfig
from src.util.constants.aws import DEFAULT_REGION
from src.util.constants.aws import SESSION_PARAMETERS

T = TypeVar('T')


class DAO(ABC):
    DEFAULT_WAIT_INTERVAL = 2.5
    DEFAULT_MAX_WAIT = 10.0

    def __init__(self):
        pass

    @property
    @abstractmethod
    def _partition_key(self) -> str:
        return self._partition_key

    @property
    def _sort_key(self) -> str:
        return ""

    @property
    @abstractmethod
    def table_name(self) -> str:
        return self.table_name

    @property
    @abstractmethod
    def _dataclass(self) -> Type[T]:
        return Type[T]

    @property
    def _table_config(self) -> TableConfig | None:
        return None

    @property
    def _session_parameters(self) -> dict:
        return SESSION_PARAMETERS

    @property
    def _session(self):
        return boto3.Session(**self._session_parameters)

    @property
    def _client(self):
        return self._session.client(DYNAMODB_SERVICE_NAME, DEFAULT_REGION)

    @property
    def _max_batch_write_size(self) -> int:
        return 25

    @staticmethod
    def _marshall(data: dict | list):
        return json.loads(dynamodb_json.dumps(data))

    @staticmethod
    def _unmarshall(data: dict):
        return dynamodb_json.loads(data)

    @property
    def _dacite_config(self) -> Config | None:
        return None

    def get_table_status(self):
        response = self._client.describe_table(TableName=self.table_name)
        description = response[TABLE_KEY]
        return description[TABLE_STATUS_KEY]

    def _table_exists(self):
        try:
            self.get_table_status()
            return True
        except botocore.exceptions.ClientError:
            return False

    def wait_for_status(self, expected_status: DynamoDBStatus,
                        interval_s: float = DEFAULT_WAIT_INTERVAL,
                        max_wait_s: float = DEFAULT_MAX_WAIT):
        start_time = time.time()
        while self.get_table_status() != expected_status.value:
            if time.time() - start_time <= max_wait_s:
                time.sleep(interval_s)
            else:
                raise Exception("Max time exceeded waiting for table")

    def _wait_for_delete(self, interval_s: float = DEFAULT_WAIT_INTERVAL,
                         max_wait_s: float = DEFAULT_MAX_WAIT):
        start_time = time.time()
        while self._table_exists():
            if time.time() - start_time < max_wait_s:
                time.sleep(interval_s)
            else:
                raise Exception("Max time exceeded waiting for table")

    def get_all_items(self, **scan_filter) -> list[Type[T]]:
        data = self._client.scan(TableName=self.table_name,
                                 ScanFilter=scan_filter)
        res = []
        if data[ITEM_COUNT_KEY] > 0:
            for item in data[ITEMS_KEY]:
                try:
                    res.append(from_dict(data_class=self._dataclass,
                                         data=self._unmarshall(item),
                                         config=self._dacite_config))
                except TypeError:
                    res.append(self._dataclass(**self._unmarshall(item)))
            return res
        return res

    def _update_item(self, item_key: str, updates: list[tuple[str, any]]):
        count = len(updates)
        update_expression = 'SET ' + ', '.join(
            [f"{updates[i][0]} = :{i}" for i in range(count)])
        attribute_values = {f":{i}": updates[i][1] for i in range(count)}
        self._client.update_item(
            TableName=self.table_name,
            Key=self._marshall({self._partition_key: item_key}),
            UpdateExpression=update_expression,
            ExpressionAttributeValues=self._marshall(attribute_values)
        )

    def batch_write_items(self, items: list[_dataclass]):
        count = len(items)
        for batch_start in range(0, count, self._max_batch_write_size):
            batch_end = min(batch_start + self._max_batch_write_size, count)
            self._client.batch_write_item(**{
                REQUEST_ITEMS_KEY: {
                    self.table_name: [
                        {
                            PUT_REQUEST_KEY: {
                                ITEM_KEY: self._marshall(
                                    dataclasses.asdict(item))
                            }
                        }
                        for item in items[batch_start: batch_end]
                    ],
                },
                RETURN_CONSUMED_CAPACITY_KEY: NONE,
                RETURN_ITEM_COLLECTION_METRICS_KEY: NONE
            })

    def delete_all_items(self):
        if not self._table_config:
            return
        self._client.delete_table(TableName=self.table_name)
        self._wait_for_delete()
        self._client.create_table(
            AttributeDefinitions=self._table_config.get_attr_def(),
            TableName=self._table_config.TableName,
            KeySchema=self._table_config.get_key_schema(),
            BillingMode=ON_DEMAND
        )
        self.wait_for_status(DynamoDBStatus.ACTIVE)

    def get_item(self, partition_key: str,
                 sort_key: str = None) -> Type[T] | None:
        key = {self._partition_key: partition_key}
        if self._sort_key:
            if sort_key:
                key[self._sort_key] = sort_key
            else:
                raise
        try:
            response = self._client.get_item(
                TableName=self.table_name,
                Key=self._marshall({self._partition_key: partition_key}),
            )
            if response and response.get(ITEM_KEY):
                return from_dict(data_class=self._dataclass,
                                 data=self._unmarshall(response[ITEM_KEY]),
                                 config=self._dacite_config)
        except botocore.exceptions.ClientError:
            return None

    def _get_item_by_key(self, partition_key_value: str) -> Type[T] | None:
        try:
            response = self._client.get_item(
                TableName=self.table_name,
                Key=self._marshall({self._partition_key: partition_key_value}),
            )
            if response:
                return from_dict(data_class=self._dataclass,
                                 data=self._unmarshall(response[ITEM_KEY]),
                                 config=self._dacite_config)
        except botocore.exceptions.ClientError:
            return None

    # def get_items(self, keys: list[str | tuple[str, str]]) -> Type[T] | None:
    #     if type(keys) == list[str] and not self._sort_key:
    #         search = [{self._partition_key: key} for key in keys]
    #     elif type(keys) == list[tuple[str, str]] and self._sort_key:
    #         search = []
    #         for key in keys:
    #             search.append({self._partition_key: key[0],
    #                            self._sort_key: key[1]})
    #     else:
    #         raise ValueError
    #     try:
    #         response = self._client.batch_get_item(
    #             TableName=self.table_name,
    #             Key=self._marshall(search),
    #         )
    #         if response and response.get(ITEM_KEY):
    #             return from_dict(data_class=self._dataclass,
    #                              data=self._unmarshall(response[ITEM_KEY]),
    #                              config=self._dacite_config)
    #     except botocore.exceptions.ClientError:
    #         return None
