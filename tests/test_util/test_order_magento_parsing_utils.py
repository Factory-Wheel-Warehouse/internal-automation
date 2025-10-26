import logging

from src.util.constants.order import ADDITIONAL_PAYMENT_INFO
from src.util.constants.order import CHANNEL_FEE
from src.util.constants.order import EXTENSION_ATTRIBUTES
from src.util.constants.order import KEY
from src.util.constants.order import VALUE
from src.util.order import magento_parsing_utils as parsing_utils


def test_get_channel_fee_extracts_value():
    order = {
        EXTENSION_ATTRIBUTES: {
            ADDITIONAL_PAYMENT_INFO: [
                {KEY: "random", VALUE: "0"},
                {KEY: CHANNEL_FEE, VALUE: "5.25"},
            ]
        }
    }

    assert parsing_utils.get_channel_fee(order) == 5.25


def test_get_channel_fee_returns_zero_when_missing():
    assert parsing_utils.get_channel_fee({}) == 0.0
    assert parsing_utils.get_channel_fee(
        {EXTENSION_ATTRIBUTES: {ADDITIONAL_PAYMENT_INFO: []}}
    ) == 0.0


def test_get_channel_fee_logs_invalid_values(caplog):
    with caplog.at_level(logging.ERROR):
        value = parsing_utils.get_channel_fee({
            EXTENSION_ATTRIBUTES: {
                ADDITIONAL_PAYMENT_INFO: [
                    {KEY: CHANNEL_FEE, VALUE: "not-a-number"},
                ]
            }
        })

    assert value == 0.0
    assert "Exception" in caplog.text
