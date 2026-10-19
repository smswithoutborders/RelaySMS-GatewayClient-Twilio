# SPDX-License-Identifier: GPL-3.0-only
"""Settings from the environment and .env."""

import os
import re
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]

# Read as comma-separated URLs, not a JSON list.
UrlList = Annotated[list[HttpUrl], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # LOAD_DOTENV=false, as in tests, skips .env.
        env_file=None if os.environ.get("LOAD_DOTENV") == "false" else ROOT / ".env",
        # A blank value, as template.env has, counts as unset.
        env_ignore_empty=True,
        # Keeps a mistyped secret out of the startup error.
        hide_input_in_errors=True,
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    twilio_auth_token: SecretStr
    sender_hash_key: SecretStr
    forward_urls_json: UrlList = []
    forward_urls_raw: UrlList = []
    forward_tag: SecretStr | None = None
    forward_timeout: int = Field(10, ge=1)

    @field_validator("sender_hash_key")
    @classmethod
    def _check_key(cls, key: SecretStr) -> SecretStr:
        if not re.fullmatch(r"[0-9a-fA-F]{64}", key.get_secret_value()):
            raise ValueError("must be 64 hex characters")
        return key

    @field_validator("forward_urls_json", "forward_urls_raw", mode="before")
    @classmethod
    def _split_urls(cls, value: object) -> object:
        if isinstance(value, str):
            return [url.strip() for url in value.split(",") if url.strip()]
        return value

    @model_validator(mode="after")
    def _require_a_url(self) -> Self:
        if not self.forward_urls_json and not self.forward_urls_raw:
            raise ValueError("set FORWARD_URLS_JSON or FORWARD_URLS_RAW")
        return self


settings = Settings()  # pyright: ignore[reportCallIssue]
