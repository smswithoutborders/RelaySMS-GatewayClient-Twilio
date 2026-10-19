# SPDX-License-Identifier: GPL-3.0-only
"""Forwards each SMS to the configured URLs."""

import asyncio
import hmac
import logging
from typing import Any, TypedDict

import httpx
import phonenumbers
from pydantic import HttpUrl

from gateway_client.config import settings

logger = logging.getLogger(__name__)


class SenderFields(TypedDict):
    address: str
    dialing_code: str | None
    iso: str | None


def sender_fields(phone: str) -> SenderFields:
    """The sender's keyed hash, calling code and region, without the number."""
    key = bytes.fromhex(settings.sender_hash_key.get_secret_value())
    address = hmac.digest(key, phone.encode(), "sha256").hex()
    try:
        number = phonenumbers.parse(phone)
    except phonenumbers.NumberParseException:
        return {"address": address, "dialing_code": None, "iso": None}
    region = phonenumbers.region_code_for_number(number)
    if region == phonenumbers.REGION_CODE_FOR_NON_GEO_ENTITY:
        region = None
    return {
        "address": address,
        "dialing_code": str(number.country_code),
        "iso": region,
    }


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=settings.forward_timeout)


async def forward(params: dict[str, Any]) -> bool:
    """Send the SMS to every URL; False if any of them failed."""
    tag = settings.forward_tag
    body = {
        **sender_fields(params["From"]),
        "text": params["Body"],
        "tag": tag.get_secret_value() if tag else None,
    }
    async with _client() as client:
        results = await asyncio.gather(
            *(_post(client, url, json=body) for url in settings.forward_urls_json),
            *(_post(client, url, data=params) for url in settings.forward_urls_raw),
        )
    return all(results)


async def _post(client: httpx.AsyncClient, url: HttpUrl, **kwargs: Any) -> bool:
    try:
        response = await client.post(str(url), **kwargs)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Failed to forward an SMS to %s: %s", url, exc)
        return False
    return True
