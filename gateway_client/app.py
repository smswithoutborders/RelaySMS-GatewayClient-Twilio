# SPDX-License-Identifier: GPL-3.0-only
"""Receives Twilio's SMS webhook and forwards each message."""

import logging
import os
import sys

from fastapi import FastAPI, HTTPException, Request, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from gateway_client import forward
from gateway_client.config import settings

# journald timestamps each line itself.
_under_journald = bool(os.getenv("JOURNAL_STREAM")) and not sys.stderr.isatty()
logging.basicConfig(
    level=settings.log_level,
    format=("" if _under_journald else "%(asctime)s - ")
    + "%(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

validator = RequestValidator(settings.twilio_auth_token.get_secret_value())
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/twilio-sms")
async def twilio_sms(request: Request) -> Response:
    params = dict(await request.form())
    signature = request.headers.get("X-Twilio-Signature", "")
    if not validator.validate(str(request.url), params, signature):
        logger.warning("Rejected a webhook with an invalid Twilio signature.")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature.")

    if not all(isinstance(params.get(field), str) for field in ("From", "Body")):
        raise HTTPException(
            status_code=400, detail="Missing required field 'From' or 'Body'."
        )

    if not await forward.forward(params):
        raise HTTPException(status_code=502, detail="Forwarding failed.")
    # Empty TwiML: no reply SMS.
    return Response(content=str(MessagingResponse()), media_type="text/xml")
