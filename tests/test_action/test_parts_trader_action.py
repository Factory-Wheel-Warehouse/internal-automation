from types import SimpleNamespace

import pytest

from src.action.scraping.parts_trader_action import PartsTraderAction


@pytest.fixture
def action(mocker):
    action = PartsTraderAction()
    action.chrome_driver = mocker.Mock()
    action.get_element = mocker.Mock()
    action.get_elements = mocker.Mock()
    action.get_child = mocker.Mock()
    action.accept_pending_quote = mocker.Mock()
    action.sort_quotes_by_parts = mocker.Mock()
    action.explicit_wait_get = mocker.Mock()
    return action


def test_login_sends_credentials(mocker, action):
    user_el = mocker.Mock()
    pass_el = mocker.Mock()
    dashboard = mocker.Mock()
    action.get_element.side_effect = [user_el, pass_el, dashboard]

    action.login()

    user_el.send_keys.assert_any_call("test-user")
    pass_el.send_keys.assert_any_call("test-pass")


def test_get_pending_quotes_filters_positive_counts(mocker, action):
    rows = ["row1", "row2"]
    action.get_elements.return_value = rows

    def fake_child(row, by, value):
        if value == "quotedParts":
            return SimpleNamespace(text="1" if row == "row1" else "0")
        link = mocker.Mock()
        link.get_property.return_value = f"http://{row}"
        return link

    action.get_child.side_effect = fake_child

    result = action.get_pending_quotes()
    assert result == ["http://row1"]


def test_accept_pending_quotes_loops_until_empty(mocker, action):
    mocker.patch.object(action, "get_pending_quotes", side_effect=[["href1"], []])

    action.accept_pending_quotes()

    assert action.accept_pending_quote.call_count == 1


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
    action.accept_pending_quotes.assert_called_once()
