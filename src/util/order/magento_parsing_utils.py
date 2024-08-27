import json
import pprint

from src.util.constants.order import ADDITIONAL_PAYMENT_INFO
from src.util.constants.order import CHANNEL_FEE
from src.util.constants.order import EXTENSION_ATTRIBUTES
from src.util.constants.order import KEY
from src.util.constants.order import VALUE


def get_channel_fee(raw_order_json: dict) -> float:
    """
    Returns the channel fee as returned by magento in the order object of
    the API response
    :param raw_order_json: dict json response representing an order object
    from the Magento API
    :return: positive float representing the channel fee
    """
    extension_attributes = raw_order_json.get(EXTENSION_ATTRIBUTES)
    if not extension_attributes:
        return 0.0

    additional_payment_info = extension_attributes.get(ADDITIONAL_PAYMENT_INFO)
    if not additional_payment_info:
        return 0.0

    for kv_pair_map in additional_payment_info:
        if kv_pair_map.get(KEY) == CHANNEL_FEE:
            try:
                return float(kv_pair_map.get(VALUE))
            except ValueError:
                print("value error")
                return 0.0
    return 0.0
