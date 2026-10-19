# SPDX-License-Identifier: GPL-3.0-only

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from gateway_client import app as app_module
from tests.conftest import AUTH_TOKEN, SMS

client = TestClient(app_module.app)


@pytest.fixture(autouse=True)
def forward(monkeypatch):
    mock = AsyncMock(return_value=True)
    monkeypatch.setattr(app_module.forward, "forward", mock)
    return mock


def _signed_post(params):
    signature = RequestValidator(AUTH_TOKEN).compute_signature(
        "http://testserver/twilio-sms", params
    )
    return client.post(
        "/twilio-sms", data=params, headers={"X-Twilio-Signature": signature}
    )


def test_forwards_a_signed_sms(forward):
    response = _signed_post(SMS)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/xml")
    forward.assert_awaited_once_with(SMS)


@pytest.mark.parametrize("headers", [{"X-Twilio-Signature": "forged"}, {}])
def test_an_unsigned_webhook_is_rejected(forward, headers):
    response = client.post("/twilio-sms", data=SMS, headers=headers)

    assert response.status_code == 403
    forward.assert_not_awaited()


def test_a_missing_body_is_rejected(forward):
    response = _signed_post({"From": "+237670000000"})

    assert response.status_code == 400
    forward.assert_not_awaited()


def test_a_failed_forward_is_a_502(forward):
    forward.return_value = False

    assert _signed_post(SMS).status_code == 502


def test_health():
    assert client.get("/health").json() == {"status": "ok"}
