"""Configuration loaded from environment variables (and an optional .env file).

Secrets are never printed. Use ``Settings.safe_summary()`` for display.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a whole number, got {raw!r}.") from exc
    if value < minimum:
        raise ConfigError(f"{name} must be at least {minimum}, got {value}.")
    return value


@dataclass(frozen=True)
class Settings:
    google_api_key: str | None
    gemini_model: str
    workspace_dir: Path
    max_file_bytes: int
    max_model_calls: int
    max_tool_calls: int
    search_max_results: int
    search_timeout: int
    llm_timeout: int

    @classmethod
    def load(cls, env_file: str | os.PathLike | None = None) -> "Settings":
        """Load settings. Environment variables already set take priority over .env."""
        load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)
        key = (os.getenv("GOOGLE_API_KEY") or "").strip()
        if key.lower() in {"", "your_api_key_here"}:
            key = ""
        workspace = Path(os.getenv("WORKSPACE_DIR") or "sample_files")
        if not workspace.is_absolute():
            workspace = PROJECT_ROOT / workspace
        return cls(
            google_api_key=key or None,
            gemini_model=(os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip(),
            workspace_dir=workspace.resolve(),
            max_file_bytes=_int_env("MAX_FILE_BYTES", 100_000),
            max_model_calls=_int_env("MAX_MODEL_CALLS", 8),
            max_tool_calls=_int_env("MAX_TOOL_CALLS", 8),
            search_max_results=_int_env("SEARCH_MAX_RESULTS", 5),
            search_timeout=_int_env("SEARCH_TIMEOUT", 15),
            llm_timeout=_int_env("LLM_TIMEOUT", 60),
        )

    def safe_summary(self) -> dict[str, str]:
        """Settings for display. The API key is reported only as set / not set."""
        return {
            "GOOGLE_API_KEY": "set" if self.google_api_key else "NOT SET",
            "GEMINI_MODEL": self.gemini_model,
            "WORKSPACE_DIR": str(self.workspace_dir),
            "MAX_FILE_BYTES": str(self.max_file_bytes),
            "MAX_MODEL_CALLS": str(self.max_model_calls),
            "MAX_TOOL_CALLS": str(self.max_tool_calls),
            "SEARCH_MAX_RESULTS": str(self.search_max_results),
            "SEARCH_TIMEOUT": f"{self.search_timeout}s",
        }
