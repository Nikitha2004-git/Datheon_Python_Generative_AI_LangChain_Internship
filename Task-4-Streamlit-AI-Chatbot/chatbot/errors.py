"""Turn raw exceptions into short, friendly messages (and hide secrets)."""

from __future__ import annotations

from typing import Optional


def redact(text: str, secret: Optional[str]) -> str:
    """Replace the API key with *** if it ever appears in an error text."""
    if secret and len(secret) >= 8:
        return text.replace(secret, "***")
    return text


def describe_error(exc: BaseException, secret: Optional[str] = None) -> str:
    """Return a beginner-friendly explanation for an exception.

    The checks are simple text matches, so they are a best guess. The generic
    fallback always shows the exception type so you can search for it.
    """
    raw = redact(str(exc), secret)
    lowered = f"{type(exc).__name__} {raw}".lower()

    if any(w in lowered for w in ("api key", "api_key_invalid", "unauthenticated",
                                  "permission_denied", "401", "403")):
        return (
            "Google rejected the API key. Check that GOOGLE_API_KEY in your .env "
            "file is correct, has no extra spaces, and that the Gemini API is "
            "enabled for it."
        )
    if any(w in lowered for w in ("429", "resource_exhausted", "quota", "rate limit")):
        return (
            "You hit the Gemini rate limit or quota. Wait a minute and try again, "
            "or set a different GEMINI_MODEL in .env."
        )
    if "404" in lowered or "not_found" in lowered or "not found" in lowered:
        return (
            "The model was not found. Check the GEMINI_MODEL value in your .env "
            "file against Google's current model list "
            "(https://ai.google.dev/gemini-api/docs/models)."
        )
    if any(w in lowered for w in ("timeout", "timed out", "connection", "connecterror",
                                  "network", "name resolution", "unreachable")):
        return (
            "Could not reach the Gemini service. Check your internet connection "
            "and try again."
        )
    if "safety" in lowered or "blocked" in lowered:
        return (
            "The model declined to answer that message (safety filter). "
            "Try rephrasing it."
        )
    return (
        f"Something went wrong while contacting the model ({type(exc).__name__}). "
        f"Details: {raw[:300]}"
    )
