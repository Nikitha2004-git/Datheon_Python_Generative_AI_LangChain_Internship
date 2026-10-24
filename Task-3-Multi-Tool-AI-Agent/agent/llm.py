"""Create the chat model (Google Gemini via langchain-google-genai)."""
from __future__ import annotations

from .config import ConfigError, Settings


class MissingAPIKeyError(ConfigError):
    """Raised when GOOGLE_API_KEY is not configured."""


def get_llm(settings: Settings):
    """Return a Gemini chat model, or raise MissingAPIKeyError with a friendly message."""
    if not settings.google_api_key:
        raise MissingAPIKeyError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and put your key in it. "
            "Get a free key at https://aistudio.google.com/apikey"
        )
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:  # pragma: no cover
        raise ConfigError(
            "langchain-google-genai is not installed. Run: pip install -r requirements.txt"
        ) from exc
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0,
        max_retries=2,
        timeout=settings.llm_timeout,
    )
