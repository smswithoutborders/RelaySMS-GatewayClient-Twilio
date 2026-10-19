# SPDX-License-Identifier: GPL-3.0-only

import asyncio
import hmac
import json

import httpx
import pytest
from pydantic import HttpUrl, SecretStr

from gateway_client import forward
from tests.conftest import SENDER_HASH_KEY, SMS


@pytest.fixture
def set_settings(monkeypatch):
    def apply(**changes):
        monkeypatch.setattr(
            forward, "settings", forward.settings.model_copy(update=changes)
        )

    return apply


@pytest.fixture
def mock_http(monkeypatch):
    """Route forward's requests to handler; returns the requests sent."""

    def apply(handler):
        sent: list[httpx.Request] = []

        def record(request: httpx.Request) -> httpx.Response:
            sent.append(request)
            return handler(request)

        transport = httpx.MockTransport(record)
        monkeypatch.setattr(
            forward, "_client", lambda: httpx.AsyncClient(transport=transport)
        )
        return sent

    return apply


def _forward() -> bool:
    return asyncio.run(forward.forward(SMS))


@pytest.mark.parametrize("tag", ["test-tag", None])
def test_sends_the_json_body_and_the_raw_form(set_settings, mock_http, tag):
    set_settings(
        forward_urls_raw=[HttpUrl("https://raw.test/hook")],
        forward_tag=SecretStr(tag) if tag else None,
    )
    sent = mock_http(lambda request: httpx.Response(200))

    assert _forward()

    by_host = {request.url.host: request for request in sent}
    address = hmac.new(bytes.fromhex(SENDER_HASH_KEY), b"+237670000000", "sha256")
    assert json.loads(by_host["json.test"].content) == {
        "address": address.hexdigest(),
        "dialing_code": "237",
        "iso": "CM",
        "text": "cGF5bG9hZA==",
        "tag": tag,
    }
    raw = by_host["raw.test"]
    assert dict(httpx.QueryParams(raw.content.decode())) == SMS


def test_a_failing_url_does_not_stop_the_others(set_settings, mock_http, caplog):
    set_settings(
        forward_urls_raw=[
            HttpUrl("https://down.test/hook"),
            HttpUrl("https://error.test/hook"),
        ],
    )

    def handler(request):
        if request.url.host == "down.test":
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(500 if request.url.host == "error.test" else 200)

    sent = mock_http(handler)

    assert not _forward()

    assert {request.url.host for request in sent} == {
        "down.test",
        "error.test",
        "json.test",
    }
    assert "down.test" in caplog.text
    assert "error.test" in caplog.text


@pytest.mark.parametrize(
    "phone, dialing_code, iso",
    [
        ("+237670000000", "237", "CM"),
        # +1 covers Canada and the US; only iso tells them apart.
        ("+15145550123", "1", "CA"),
        ("+80012345678", "800", None),
        ("Twilio", None, None),
    ],
)
def test_sender_fields(phone, dialing_code, iso):
    fields = forward.sender_fields(phone)

    assert (fields["dialing_code"], fields["iso"]) == (dialing_code, iso)
