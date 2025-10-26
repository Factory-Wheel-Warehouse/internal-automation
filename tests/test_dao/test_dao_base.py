from dataclasses import dataclass
from typing import Type

import pytest

from src.dao.dao import DAO
from src.util.aws.dynamodb.constants import (
    ITEMS_KEY,
    ITEM_COUNT_KEY,
    TABLE_KEY,
    TABLE_STATUS_KEY,
)


@dataclass
class SampleItem:
    pk: str
    value: int


class SampleDAO(DAO):
    @property
    def _partition_key(self) -> str:
        return "pk"

    @property
    def table_name(self) -> str:
        return "sample-table"

    @property
    def _dataclass(self) -> Type[SampleItem]:
        return SampleItem


@pytest.fixture
def sample_dao(monkeypatch, stubbed_boto3_session):
    # Ensure the fake dynamodb client exists before DAO usage
    stubbed_boto3_session.client("dynamodb")
    monkeypatch.setattr(SampleDAO, "_marshall", staticmethod(lambda data: data))
    monkeypatch.setattr(SampleDAO, "_unmarshall", staticmethod(lambda data: data))
    return SampleDAO()


def test_get_table_status(sample_dao, stubbed_boto3_session):
    client = stubbed_boto3_session.client("dynamodb")
    client.describe_table.return_value = {
        TABLE_KEY: {TABLE_STATUS_KEY: "ACTIVE"}
    }

    assert sample_dao.get_table_status() == "ACTIVE"
    client.describe_table.assert_called_once_with(
        TableName=sample_dao.table_name
    )


def test_get_all_items_returns_dataclasses(sample_dao, stubbed_boto3_session):
    client = stubbed_boto3_session.client("dynamodb")
    client.scan.return_value = {
        ITEM_COUNT_KEY: 1,
        ITEMS_KEY: [{"pk": "1", "value": 2}],
    }

    items = sample_dao.get_all_items()

    assert items == [SampleItem(pk="1", value=2)]
    client.scan.assert_called_once()


def test_update_item_builds_update_expression(sample_dao, stubbed_boto3_session):
    client = stubbed_boto3_session.client("dynamodb")

    sample_dao._update_item("item-1", [("attr_one", "foo"), ("attr_two", 5)])

    client.update_item.assert_called_once_with(
        TableName="sample-table",
        Key={"pk": "item-1"},
        UpdateExpression="SET attr_one = :0, attr_two = :1",
        ExpressionAttributeValues={":0": "foo", ":1": 5},
    )


def test_batch_write_items_chunks_requests(sample_dao, stubbed_boto3_session):
    client = stubbed_boto3_session.client("dynamodb")
    items = [SampleItem(pk=str(i), value=i) for i in range(30)]

    sample_dao.batch_write_items(items)

    assert client.batch_write_item.call_count == 2
    batched_lengths = [
        len(call.kwargs["RequestItems"][sample_dao.table_name])
        for call in client.batch_write_item.call_args_list
    ]
    assert batched_lengths == [25, 5]
