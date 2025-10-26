from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

DEFAULT_ENV = {
    "AWS_ACCESS_KEY_ID": "test-access-key",
    "AWS_SECRET_ACCESS_KEY": "test-secret-key",
    "AWS_SESSION_TOKEN": "test-session",
    "AWS_DEFAULT_REGION": "us-east-1",
    "FWW_ENV": "test",
    "PARTS_TRADER_USER": "test-user",
    "PARTS_TRADER_PASS": "test-pass",
}


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    for key, value in DEFAULT_ENV.items():
        monkeypatch.setenv(key, value)
    yield


@pytest.fixture(autouse=True)
def stubbed_boto3_session(monkeypatch):
    """
    Prevent real AWS calls by replacing boto3.Session with a lightweight stub.
    """
    import boto3

    class _StubSession:
        def __init__(self):
            self.clients: Dict[str, MagicMock] = {}

        def client(self, service_name: str, region_name: str | None = None):
            client = self.clients.get(service_name)
            if not client:
                client = MagicMock(name=f"{service_name}_client")
                self.clients[service_name] = client
            return client

    session = _StubSession()
    monkeypatch.setattr(boto3, "Session", lambda **_: session)
    return session


@pytest.fixture
def fake_selenium_element():
    """
    Minimal stand-in for selenium WebElement objects used in scraping actions.
    """
    return MagicMock()


@pytest.fixture
def freezer():
    """
    Provide a FrozenDateTimeFactory so tests can adjust time deterministically.
    """
    with freeze_time("2020-01-01T00:00:00Z") as frozen_datetime:
        yield frozen_datetime


@pytest.fixture(scope="session")
def tests_data_dir(project_root: Path) -> Path:
    return project_root / "tests" / "mock"
