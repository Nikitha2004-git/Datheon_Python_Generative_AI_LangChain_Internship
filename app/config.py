"""Configuration loaded from environment variables / a local .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from dotenv import load_dotenv

from app.errors import ConfigError

DEFAULT_MODEL = "gemini-2.5-flash"
PLACEHOLDER_KEYS = {"", "your_api_key_here", "your-api-key", "changeme"}


@dataclass(frozen=True)
class Settings:
    """Application settings. The API key is never printed (see __repr__)."""

    api_key: str | None
    model: str = DEFAULT_MODEL
    timeout_seconds: int = 60
    max_input_chars: int = 20_000
    max_file_bytes: int = 200_000
    provider_name: str = "Google Gemini"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def require_api_key(self) -> str:
        """Return the key or raise a helpful error."""
        if not self.api_key:
            raise ConfigError(
                'Gemini API key is missing. Add your key to the local ".env" file '
                "and restart the application."
            )
        return self.api_key

    def __repr__(self) -> str:  # hides the key if someone prints Settings
        return (
            f"Settings(api_key={'<set>' if self.api_key else '<missing>'}, "
            f"model={self.model!r}, timeout_seconds={self.timeout_seconds})"
        )


def _int_from_env(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{name} in your .env file must be a whole number.") from None
    if value <= 0:
        raise ConfigError(f"{name} in your .env file must be greater than zero.")
    return value


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build Settings. Pass `env` in tests; otherwise .env + os.environ are used."""
    if env is None:
        load_dotenv(override=False)  # real environment variables win over .env
        env = os.environ
    key = env.get("GEMINI_API_KEY", "").strip()
    if key.lower() in PLACEHOLDER_KEYS:
        key = ""
    return Settings(
        api_key=key or None,
        model=env.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL,
        timeout_seconds=_int_from_env(env, "REQUEST_TIMEOUT_SECONDS", 60),
        max_input_chars=_int_from_env(env, "MAX_INPUT_CHARS", 20_000),
        max_file_bytes=_int_from_env(env, "MAX_FILE_BYTES", 200_000),
    )
