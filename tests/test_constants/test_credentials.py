from importlib import reload

import src.util.constants.credentials as creds


def test_credentials_module_sets_expected_fields(monkeypatch):
    monkeypatch.setenv("FTP-PW", "ftp-pass")
    monkeypatch.setenv("FISHBOWL-PW", "fish-pass")
    monkeypatch.setenv("OUTLOOK-PW", "out-pass")
    monkeypatch.setenv("OUTLOOK-CS", "out-secret")
    monkeypatch.setenv("MAGENTO_AT", "magento-token")

    module = reload(creds)

    assert module.FTP_CREDENTIALS["password"] == "ftp-pass"
    assert module.FISHBOWL_CREDENTIALS["password"] == "fish-pass"
    assert module.OUTLOOK_CREDENTIALS["password"] == "out-pass"
    assert module.MAGENTO_CREDENTIALS["accessToken"] == "magento-token"
