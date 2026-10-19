# SPDX-License-Identifier: GPL-3.0-only

import pytest
from pydantic import ValidationError

from gateway_client.config import Settings
from tests.conftest import SENDER_HASH_KEY


def _load() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


def _errors() -> str:
    with pytest.raises(ValidationError) as error:
        _load()
    return str(error.value)


def test_every_missing_variable_is_reported(monkeypatch):
    for name in ("TWILIO_AUTH_TOKEN", "SENDER_HASH_KEY"):
        monkeypatch.delenv(name)

    message = _errors()

    assert "twilio_auth_token" in message
    assert "sender_hash_key" in message


def test_at_least_one_url_is_required(monkeypatch):
    monkeypatch.delenv("FORWARD_URLS_JSON")

    assert "set FORWARD_URLS_JSON or FORWARD_URLS_RAW" in _errors()


def test_a_bad_hash_key_is_rejected_without_echoing_it(monkeypatch):
    monkeypatch.setenv("SENDER_HASH_KEY", "not-the-secret")

    message = _errors()

    assert "must be 64 hex characters" in message
    assert "not-the-secret" not in message


def test_urls_are_comma_separated_http_urls(monkeypatch):
    monkeypatch.setenv("FORWARD_URLS_RAW", "https://a.test/hook, https://b.test/hook")
    assert [url.host for url in _load().forward_urls_raw] == ["a.test", "b.test"]

    monkeypatch.setenv("FORWARD_URLS_RAW", "https://ok.test,ftp://bad.test")
    assert "forward_urls_raw" in _errors()


def test_blank_values_fall_back_to_defaults(monkeypatch):
    monkeypatch.setenv("FORWARD_TAG", "")
    monkeypatch.setenv("FORWARD_TIMEOUT", "")

    settings = _load()

    assert settings.forward_tag is None
    assert settings.forward_timeout == 10


def test_the_timeout_must_be_positive(monkeypatch):
    monkeypatch.setenv("FORWARD_TIMEOUT", "0")

    assert "forward_timeout" in _errors()


def test_an_env_file_with_server_settings_loads(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("HOST=127.0.0.1\nPORT=16100\nLOG_LEVEL=DEBUG\n")

    settings = Settings(_env_file=env_file)  # pyright: ignore[reportCallIssue]

    assert settings.log_level == "DEBUG"


def test_secrets_stay_out_of_repr():
    text = repr(_load())

    for secret in ("test-auth-token", SENDER_HASH_KEY, "test-tag"):
        assert secret not in text
