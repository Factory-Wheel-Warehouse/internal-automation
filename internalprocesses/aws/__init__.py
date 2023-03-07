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
    table = dynamodb.Table("internal_automation_vendor_config")
    table_data = table.scan()
    vendor_configs = table_data.get("Items")
    if not vendor_configs:
        raise Exception("No vendor configs received from DynamoDB")
    for vendor_config in vendor_configs:
        _replace_decimal(vendor_config)
    return [VendorConfig(**vendor_config) for vendor_config in vendor_configs]
