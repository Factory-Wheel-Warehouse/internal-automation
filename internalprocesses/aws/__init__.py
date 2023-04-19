import os
from pprint import pprint

import boto3

from internalprocesses.aws.constants import *
from internalprocesses.vendor import VendorConfig

_aws_session = boto3.Session(**SESSION_PARAMETERS)


def _replace_decimal(dict_):
    for key, value in dict_.items():
        if type(value) != dict:
            try:
                if float(value) % 1 == 0:
                    dict_[key] = int(value)
                else:
                    dict_[key] = float(value)
            except ValueError:
                pass
        else:
            _replace_decimal(value)


def get_vendor_config_data():
    dynamodb = _aws_session.resource("dynamodb", DEFAULT_REGION)
    table = dynamodb.Table(DYNAMODB_VENDOR_CONFIG_TABLE)
    table_data = table.scan()
    vendor_configs = table_data.get(DYNAMODB_ITEM_KEY)
    if not vendor_configs:
        raise Exception("No vendor configs received from DynamoDB")
    for vendor_config in vendor_configs:
        _replace_decimal(vendor_config)
    return [VendorConfig(**vendor_config) for vendor_config in vendor_configs]


def post_exception_to_sns(exception_message):
    sns = _aws_session.client("sns", DEFAULT_REGION)
    sns.publish(TopicArn=SNS_EXCEPTION_TOPIC_ARN,
                Message=exception_message,
                Subject=SNS_EXCEPTION_SUBJECT)


def add_po():
    po_document = {
        "customer_po": 15,
        "hollander": "",
        "u_code": "",
        "vendor_name": "",
        "po_creation": "",
        "po_fulfill": ""
    }
