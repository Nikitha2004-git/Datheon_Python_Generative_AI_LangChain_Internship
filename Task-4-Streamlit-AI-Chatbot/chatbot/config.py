"""Configuration for the chatbot.

All settings come from environment variables. For local development they are
usually stored in a `.env` file (see `.env.example`), which is loaded with
python-dotenv. The API key is NEVER hardcoded anywhere in this project.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional

from dotenv import load_dotenv

# Folder that contains app.py (the Task-4-Streamlit-AI-Chatbot folder).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Stable Gemini model code from Google's model list (checked 22 Oct 2026).
# Change it with GEMINI_MODEL in your .env file - no code changes needed.
DEFAULT_MODEL = "gemini-3.5-flash-lite"

# How many of the most recent messages are sent to the model on each turn.
DEFAULT_MAX_HISTORY_MESSAGES = 20

# Longest message a user may send (protects against accidental huge pastes).
MAX_USER_INPUT_CHARS = 4000

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, friendly AI assistant inside a chat app. "
    "Give clear, accurate answers. Keep replies concise unless the user asks "
    "for detail. If you are not sure about something, say so instead of guessing."
)

MISSING_KEY_MESSAGE = (
    "GOOGLE_API_KEY is missing. Copy `.env.example` to `.env`, paste your Gemini "
    "API key into it, and restart the app. You can create a key at "
    "https://aistudio.google.com/apikey"
)
PLACEHOLDER_KEY_MESSAGE = (
    "GOOGLE_API_KEY is still the placeholder value. Open your `.env` file, "
    "replace it with your real Gemini API key, and restart the app."
)

# Values people commonly leave in .env by mistake.
_PLACEHOLDER_KEYS = {
    "your_api_key_here",
    "your-api-key-here",
    "paste_your_key_here",
    "changeme",
}


class ConfigError(Exception):
    """Raised when the app cannot start a model because of bad configuration."""


@dataclass(frozen=True)
class AppConfig:
    """Validated settings used by the app."""

    # repr=False so the key can never show up in logs or tracebacks by accident.
    google_api_key: str = field(default="", repr=False)
    model_name: str = DEFAULT_MODEL
    temperature: Optional[float] = None  # None = use the model's own default
    max_history_messages: int = DEFAULT_MAX_HISTORY_MESSAGES
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    # Optional Task 3 agent integration (off by default).
    enable_task3_agent: bool = False
    task3_agent_dir: Path = PROJECT_ROOT.parent / "Task-3-Multi-Tool-AI-Agent"
    task3_agent_module: str = "agent"
    task3_agent_function: str = "run_agent"
    # Blocking problems (app cannot call the model) and non-blocking warnings.
    errors: tuple = ()
    warnings: tuple = ()

    @property
    def has_api_key(self) -> bool:
        return bool(self.google_api_key)


def _parse_bool(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def load_config(
    env: Optional[Mapping[str, str]] = None,
    dotenv_path: Optional[Path] = None,
) -> AppConfig:
    """Build an AppConfig. This function never raises.

    Problems are collected in `config.errors` (blocking) and `config.warnings`
    so the UI can show friendly messages instead of crashing.

    If `env` is None, the `.env` file is loaded and `os.environ` is used.
    Tests pass their own `env` dict, so no real `.env` or API key is needed.
    """
    if env is None:
        # override=False: real environment variables win over the .env file.
        load_dotenv(dotenv_path or (PROJECT_ROOT / ".env"), override=False)
        env = os.environ

    errors: list = []
    warnings: list = []

    # --- API key ---------------------------------------------------------
    api_key = (env.get("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        errors.append(MISSING_KEY_MESSAGE)
    elif api_key.lower() in _PLACEHOLDER_KEYS:
        errors.append(PLACEHOLDER_KEY_MESSAGE)
        api_key = ""

    # --- Model name ------------------------------------------------------
    model_name = (env.get("GEMINI_MODEL") or "").strip() or DEFAULT_MODEL

    # --- Temperature (optional) -----------------------------------------
    temperature: Optional[float] = None
    raw_temp = (env.get("GEMINI_TEMPERATURE") or "").strip()
    if raw_temp:
        try:
            temperature = float(raw_temp)
            if not 0.0 <= temperature <= 2.0:
                raise ValueError
        except ValueError:
            warnings.append(
                f"GEMINI_TEMPERATURE='{raw_temp}' is not a number between 0 and 2; "
                "using the model default."
            )
            temperature = None

    # --- Conversation memory window -------------------------------------
    max_history = DEFAULT_MAX_HISTORY_MESSAGES
    raw_hist = (env.get("MAX_HISTORY_MESSAGES") or "").strip()
    if raw_hist:
        try:
            max_history = int(raw_hist)
            if max_history < 1:
                raise ValueError
        except ValueError:
            warnings.append(
                f"MAX_HISTORY_MESSAGES='{raw_hist}' must be a whole number >= 1; "
                f"using {DEFAULT_MAX_HISTORY_MESSAGES}."
            )
            max_history = DEFAULT_MAX_HISTORY_MESSAGES

    system_prompt = (env.get("SYSTEM_PROMPT") or "").strip() or DEFAULT_SYSTEM_PROMPT

    # --- Optional Task 3 agent -------------------------------------------
    agent_dir_raw = (env.get("TASK3_AGENT_DIR") or "").strip()
    if agent_dir_raw:
        agent_dir = Path(agent_dir_raw)
        if not agent_dir.is_absolute():
            agent_dir = PROJECT_ROOT / agent_dir
    else:
        agent_dir = PROJECT_ROOT.parent / "Task-3-Multi-Tool-AI-Agent"

    return AppConfig(
        google_api_key=api_key,
        model_name=model_name,
        temperature=temperature,
        max_history_messages=max_history,
        system_prompt=system_prompt,
        enable_task3_agent=_parse_bool(env.get("ENABLE_TASK3_AGENT")),
        task3_agent_dir=agent_dir,
        task3_agent_module=(env.get("TASK3_AGENT_MODULE") or "").strip() or "agent",
        task3_agent_function=(env.get("TASK3_AGENT_FUNCTION") or "").strip()
        or "run_agent",
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
