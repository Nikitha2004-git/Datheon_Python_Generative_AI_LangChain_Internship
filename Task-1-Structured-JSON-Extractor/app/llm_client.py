"""AI provider communication. Only this module knows about Gemini.

To add another provider, subclass LLMClient and change `create_client`.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.config import Settings
from app.errors import ConfigError, LLMError

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    provider_name: str = "Unknown"

    @abstractmethod
    def generate_json(self, system_instruction: str, prompt: str) -> str:
        """Send the prompt and return the raw text of the model's reply."""


def translate_api_error(code: int | None, message: str) -> LLMError:
    """Map an HTTP-style API error to a friendly message (no raw details)."""
    lowered = (message or "").lower()
    if code in (401, 403) or (code == 400 and "api key" in lowered):
        return LLMError(
            'The Gemini API key was rejected. Check the key in your ".env" file.'
        )
    if code == 429:
        if "quota" in lowered or "billing" in lowered:
            return LLMError(
                "Your Gemini API quota is exhausted. Wait for it to reset or check "
                "your plan in Google AI Studio."
            )
        return LLMError("Gemini rate limit reached. Please wait a minute and retry.")
    if code in (408, 504):
        return LLMError("The AI request timed out. Please try again.")
    if code is not None and code >= 500:
        return LLMError("The Gemini service is temporarily unavailable. Try again soon.")
    if code == 404:
        return LLMError(
            "The configured Gemini model was not found. Check GEMINI_MODEL in .env."
        )
    return LLMError(f"The Gemini API returned an error (code {code}). Please try again.")


class GeminiClient(LLMClient):
    provider_name = "Google Gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: int = 60) -> None:
        from google import genai
        from google.genai import types

        self._model = model
        self._types = types
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_seconds * 1000),
        )

    def generate_json(self, system_instruction: str, prompt: str) -> str:
        import httpx
        from google.genai import errors

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            text = response.text
        except errors.APIError as exc:
            logger.warning("Gemini API error code=%s", getattr(exc, "code", None))
            raise translate_api_error(
                getattr(exc, "code", None), str(getattr(exc, "message", "") or exc)
            ) from None
        except httpx.TimeoutException:
            raise LLMError("The AI request timed out. Please try again.") from None
        except httpx.TransportError:
            raise LLMError(
                "Could not reach the Gemini API. Check your internet connection."
            ) from None
        except Exception as exc:  # noqa: BLE001 - last-resort safety net
            logger.warning("Unexpected provider error: %s", type(exc).__name__)
            raise LLMError("Unexpected error while calling the AI. Please try again.") from None
        if not isinstance(text, str) or not text.strip():
            raise LLMError("The AI returned an empty response. Please try again.")
        return text


def create_client(settings: Settings) -> LLMClient:
    """Build the configured client, or raise a helpful ConfigError."""
    api_key = settings.require_api_key()
    return GeminiClient(api_key, settings.model, settings.timeout_seconds)
