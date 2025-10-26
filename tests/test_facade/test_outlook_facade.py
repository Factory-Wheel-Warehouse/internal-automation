from types import SimpleNamespace

import pytest

from src.facade.outlook.outlook_facade import OutlookFacade


class DummyApp:
    def __init__(self, silent_token=None, password_token=None):
        self._silent = silent_token
        self._password = password_token
        self.password_calls = 0

    def get_accounts(self, username):
        return ["account"]

    def acquire_token_silent(self, scope, account):
        return self._silent

    def acquire_token_by_username_password(self, username, password, scopes):
        self.password_calls += 1
        return self._password


def test_get_access_token_prefers_silent(monkeypatch):
    facade = OutlookFacade()
    app = DummyApp(silent_token={"access_token": "abc"})

    token = facade.getAccessToken(app, OutlookFacade.DATA)

    assert token == "abc"
    assert app.password_calls == 0


def test_get_access_token_falls_back_to_password(monkeypatch):
    facade = OutlookFacade()
    app = DummyApp(
        silent_token=None,
        password_token={"access_token": "xyz"},
    )

    token = facade.getAccessToken(app, OutlookFacade.DATA)

    assert token == "xyz"
    assert app.password_calls == 1


def test_login_sets_headers(mocker):
    facade = OutlookFacade()
    mocker.patch.object(facade, "getClientApp", return_value="app")
    mocker.patch.object(facade, "getAccessToken", return_value="token")

    facade.login()

    assert facade.headers == {"Authorization": "Bearer token"}


def test_get_email_attachments_handles_empty(mocker):
    facade = OutlookFacade()
    facade.headers = {}
    mock_get = mocker.patch(
        "src.facade.outlook.outlook_facade.requests.get",
        return_value=SimpleNamespace(json=lambda: {"value": None}),
    )

    attachments = facade.get_email_attachments("123")

    assert attachments == []
    mock_get.assert_called_once()


def test_add_cc_recipients_supports_string_and_list():
    facade = OutlookFacade()
    payload = {"message": {"ccRecipients": []}}
    facade.addCCRecipients(payload, "foo@example.com")
    assert payload["message"]["ccRecipients"][0]["emailAddress"]["address"] == \
        "foo@example.com"

    facade.addCCRecipients(payload, ["bar@example.com"])
    assert payload["message"]["ccRecipients"][1]["emailAddress"]["address"] == \
        "bar@example.com"


def test_send_mail_attaches_files(mocker):
    facade = OutlookFacade()
    facade.headers = {"Authorization": "Bearer token"}
    mock_post = mocker.patch(
        "src.facade.outlook.outlook_facade.requests.post",
        return_value="sent",
    )

    facade.sendMail(
        to="sales@example.com",
        subject="Hello",
        body="World",
        cc=["cc@example.com"],
        attachment="YmFzZTY0",
        attachmentName="report.csv",
    )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["message"]["subject"] == "Hello"
    assert payload["message"]["attachments"][0]["name"] == "report.csv"
    assert payload["message"]["ccRecipients"]
