from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from selenium.webdriver import Keys

from src.action.scraping.parts_trader_action import PartsTraderAction
from src.util.constants.scraping import (
    A,
    PARTS_TRADER_LOGIN_URL,
    PARTS_TRADER_QUOTES_URL,
    QUOTED_PARTS_CLASS,
)


def test_login_enters_credentials(monkeypatch):
    action = PartsTraderAction()
    action.explicit_wait_get = MagicMock()
    user_field = MagicMock()
    pass_field = MagicMock()
    dashboard = MagicMock()
    action.get_element = MagicMock(
        side_effect=[user_field, pass_field, dashboard]
    )

    action.login()

    action.explicit_wait_get.assert_called_once_with(PARTS_TRADER_LOGIN_URL)
    user_field.send_keys.assert_any_call("test-user")
    pass_field.send_keys.assert_any_call("test-pass")
    pass_field.send_keys.assert_any_call(Keys.ENTER)


def test_accept_pending_quotes_processes_until_empty(mocker):
    action = PartsTraderAction()
    action.explicit_wait_get = mocker.Mock()
    action.sort_quotes_by_parts = mocker.Mock()
    action.get_pending_quotes = mocker.Mock(
        side_effect=[["href-1", "href-2"], []]
    )
    action.accept_pending_quote = mocker.Mock()

    action.accept_pending_quotes()

    action.explicit_wait_get.assert_called()
    assert action.accept_pending_quote.call_count == 2
    action.accept_pending_quote.assert_any_call("href-1")
    action.accept_pending_quote.assert_any_call("href-2")


def test_get_pending_quotes_filters_positive_counts(mocker):
    action = PartsTraderAction()
    rows = ["row-1", "row-2"]
    action.get_elements = mocker.Mock(return_value=rows)

    def fake_get_child(row, by, value):
        data = {
            "row-1": {"count": "1", "href": "http://quote-1"},
            "row-2": {"count": "0", "href": "http://quote-2"},
        }

        if value == QUOTED_PARTS_CLASS:
            child = SimpleNamespace()
            child.text = data[row]["count"]
            return child

        if value == A:
            child = MagicMock()
            child.get_property.return_value = data[row]["href"]
            return child

    action.get_child = mocker.Mock(side_effect=fake_get_child)

    filtered = action.get_pending_quotes()

    assert filtered == ["http://quote-1"]


def test_accept_pending_quote_clicks_button(mocker):
    action = PartsTraderAction()
    action.explicit_wait_get = mocker.Mock()
    button = mocker.Mock()
    action.get_element = mocker.Mock(return_value=button)
    mocker.patch("src.action.scraping.parts_trader_action.time.sleep")

    action.accept_pending_quote("http://example")

    action.explicit_wait_get.assert_called_once_with("http://example")
    button.click.assert_called_once()


def test_run_calls_setup_login_and_accept(mocker):
    action = PartsTraderAction()
    action.setup = mocker.Mock()
    action.login = mocker.Mock()
    action.accept_pending_quotes = mocker.Mock()

    action.run(request_=None)

    action.setup.assert_called_once()
    action.login.assert_called_once()
    action.accept_pending_quotes.assert_called_once()
