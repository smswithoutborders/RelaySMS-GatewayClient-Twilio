# SPDX-License-Identifier: GPL-3.0-only

import os

AUTH_TOKEN = "test-auth-token"
SENDER_HASH_KEY = "cd" * 32
SMS = {"From": "+237670000000", "Body": "cGF5bG9hZA==", "MessageSid": "SM123"}

# Must be set before gateway_client.config is imported.
os.environ.update(
    LOAD_DOTENV="false",
    TWILIO_AUTH_TOKEN=AUTH_TOKEN,
    SENDER_HASH_KEY=SENDER_HASH_KEY,
    FORWARD_URLS_JSON="https://json.test/hook",
    FORWARD_TAG="test-tag",
)
