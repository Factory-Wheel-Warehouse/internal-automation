from src.action.action import Action
from src.manager.manager import Manager


class DummyAction(Action):
    def __init__(self, async_: bool = False, response=None, raise_error=False):
        self._async = async_
        self.response = response if response is not None else {"status": "ok"}
        self.raise_error = raise_error
        self.calls = []

    @property
    def async_(self):
        return self._async

    def run(self, request_):
        self.calls.append(request_)
        if self.raise_error:
            raise ValueError("boom")
        return self.response


class LeafManager(Manager):
    def __init__(self):
        self._actions = []
        self._sub_managers = []
        super().__init__()

    def get_actions(self):
        return self._actions

    def get_sub_managers(self):
        return self._sub_managers


class ParentManager(Manager):
    def __init__(self, action: Action, sub_manager: Manager):
        self._actions = [action]
        self._sub_managers = [sub_manager]
        super().__init__()

    def get_actions(self):
        return self._actions

    def get_sub_managers(self):
        return self._sub_managers


def test_manager_name_formats_class_name():
    leaf = LeafManager()
    assert leaf.name == "leaf"


def test_list_includes_actions_and_sub_managers():
    parent = ParentManager(DummyAction(async_=False), LeafManager())
    listing = parent.list()

    assert listing["actions"] == ["dummy"]
    assert listing["managers"] == {"leaf": "No endpoints implemented for this process yet"}


def test_make_handler_executes_sync_action(monkeypatch):
    action = DummyAction(async_=False, response={"done": True})
    handler = Manager.make_handler(action)
    monkeypatch.setattr("src.manager.manager.request", "fake-request")

    assert handler() == {"done": True}
    assert action.calls == ["fake-request"]


def test_make_handler_returns_error_on_exception(monkeypatch):
    action = DummyAction(async_=False, raise_error=True)
    handler = Manager.make_handler(action)
    monkeypatch.setattr("src.manager.manager.request", "req")

    assert handler() == ({"error": "boom"}, 500)


def test_make_handler_submits_async_action(monkeypatch):
    action = DummyAction(async_=True)
    submitted = []

    class FakeFuture:
        def add_done_callback(self, cb):
            self._cb = cb

    class FakeExecutor:
        def submit(self, fn):
            submitted.append(fn)
            fn()
            return FakeFuture()

    monkeypatch.setattr("src.manager.manager.request", "async-request")
    monkeypatch.setattr("src.manager.manager.executor", FakeExecutor())
    monkeypatch.setattr("src.manager.manager.copy_current_request_context", lambda f: f)

    handler = Manager.make_handler(action)
    assert handler() == ("Submitted", 202)
    assert submitted  # ensure function submitted
    assert action.calls == ["async-request"]
