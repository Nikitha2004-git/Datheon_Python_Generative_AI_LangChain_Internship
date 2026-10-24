"""Streaming helpers.

`stream_to_placeholder` reads chunks from the model and redraws one Streamlit
placeholder as the text grows. The placeholder only needs two methods,
`.markdown(text)` and `.empty()`, so tests can use a tiny fake object.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from chatbot.errors import describe_error

CURSOR = " ▌"
EMPTY_REPLY_MESSAGE = (
    "The model returned an empty reply. This can happen when a safety filter "
    "blocks the answer. Please try rephrasing your message."
)


@dataclass
class StreamResult:
    """Outcome of one assistant turn."""

    text: str = ""
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


def chunk_to_text(chunk) -> str:
    """Extract plain text from a LangChain chunk.

    Gemini can return `content` as a string OR as a list of content blocks.
    We keep only text blocks, so "thinking" blocks are never shown.
    """
    content = getattr(chunk, "content", chunk)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return ""


def stream_to_placeholder(
    chunks: Iterable, placeholder, secret: Optional[str] = None
) -> StreamResult:
    """Show chunks live in `placeholder` and return the full text.

    On failure the placeholder is cleared, so a half-finished answer is never
    left on screen next to the error message (no duplicate or partial replies).
    """
    text = ""
    try:
        for chunk in chunks:
            piece = chunk_to_text(chunk)
            if not piece:
                continue
            text += piece
            placeholder.markdown(text + CURSOR)
    except Exception as exc:  # noqa: BLE001 - we want to catch every API failure
        placeholder.empty()
        return StreamResult(text="", error=describe_error(exc, secret))

    if not text.strip():
        placeholder.empty()
        return StreamResult(text="", error=EMPTY_REPLY_MESSAGE)

    placeholder.markdown(text)  # final render without the cursor
    return StreamResult(text=text)
