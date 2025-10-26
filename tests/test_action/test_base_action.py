from types import SimpleNamespace

import pytest

from src.action.action import Action


class DummyAction(Action):
    def __init__(self, async_=True, should_raise=False):
        self._async = async_
        self.should_raise = should_raise
        self.called_with = None

    @property
    def async_(self):
        return self._async

    def run(self, request_):
        if self.should_raise:
            raise ValueError("boom")
        self.called_with = request_
        return {"ok": True}


def test_route_formats_class_name():
    action = DummyAction()
    assert action.route == "dummy"


def test_trigger_returns_response_when_sync(monkeypatch):
    request = SimpleNamespace(args=SimpleNamespace(to_dict=lambda: {}))
    action = DummyAction(async_=False)

    result = action.trigger(request)

    assert result == {"ok": True}
    assert action.called_with is request


def test_trigger_returns_submitted_when_async(monkeypatch):
    request = SimpleNamespace(args=SimpleNamespace(to_dict=lambda: {}))
    action = DummyAction(async_=True)
    result = action.trigger(request)
    assert result == ("Submitted", 202)


def test_trigger_logs_exception_and_sends_sns(mocker):
    request = SimpleNamespace(args=SimpleNamespace(to_dict=lambda: {}))
    action = DummyAction(async_=False, should_raise=True)
    post_sns = mocker.patch("src.action.action.post_exception_to_sns")

    action.trigger(request)

    post_sns.assert_called_once()


def test_get_args_returns_request_args():
    action = DummyAction()
    request = SimpleNamespace(args=SimpleNamespace(to_dict=lambda: {"a": 1}))
    assert action._get_args(request) == {"a": 1}
