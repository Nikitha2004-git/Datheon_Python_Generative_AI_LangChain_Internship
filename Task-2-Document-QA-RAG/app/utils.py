"""Small helpers shared across modules."""

from __future__ import annotations

import hashlib
import re
import uuid


class DocumentQAError(Exception):
    """Base class for errors we show to the user in friendly form."""


class DocumentLoadError(DocumentQAError):
    """A file could not be read (wrong type, empty, corrupt, too large...)."""


class ConfigurationError(DocumentQAError):
    """Something in setup is missing, e.g. the API key."""


class AnswerGenerationError(DocumentQAError):
    """Gemini could not produce an answer (rate limit, network, ...)."""


def file_hash(data: bytes) -> str:
    """SHA-256 fingerprint of file bytes. Same file -> same hash."""
    return hashlib.sha256(data).hexdigest()


def new_session_id() -> str:
    return uuid.uuid4().hex[:12]


def collection_name_for(session_id: str) -> str:
    """Chroma collection names must be 3-512 chars of [a-zA-Z0-9._-]."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", session_id) or "default"
    return f"session_{safe}"


def format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"
