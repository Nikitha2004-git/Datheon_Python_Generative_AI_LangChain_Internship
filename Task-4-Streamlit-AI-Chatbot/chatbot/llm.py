"""Google Gemini through LangChain (`langchain-google-genai`).

The import of `langchain_google_genai` happens inside the function, so the rest
of the app (and the tests) can be imported even if the package is missing.
"""

from __future__ import annotations

from typing import Iterator

from chatbot.config import AppConfig, ConfigError


def create_chat_model(config: AppConfig):
    """Create the LangChain Gemini chat model from the validated config.

    Creating the object does not call the API; no network is used here.
    """
    if not config.has_api_key:
        raise ConfigError(config.errors[0] if config.errors else "GOOGLE_API_KEY is missing.")

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:
        raise ConfigError(
            "The package 'langchain-google-genai' is not installed. "
            "Run: pip install -r requirements.txt"
        ) from exc

    kwargs = {"model": config.model_name, "google_api_key": config.google_api_key}
    if config.temperature is not None:
        kwargs["temperature"] = config.temperature
    return ChatGoogleGenerativeAI(**kwargs)


def stream_chunks(model, messages: list) -> Iterator:
    """Yield chunks from LangChain's `.stream()` interface as they arrive."""
    yield from model.stream(messages)
