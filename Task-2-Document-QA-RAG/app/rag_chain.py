"""The RAG pipeline: retrieve -> build context -> ask Gemini -> package answer."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.config import Settings
from app.prompts import (
    INSUFFICIENT_MARKER,
    NO_DOCUMENTS_MESSAGE,
    NO_INFO_MESSAGE,
    SYSTEM_PROMPT,
    USER_PROMPT,
    format_context,
)
from app.retriever import RetrievedChunk, retrieve
from app.utils import AnswerGenerationError, ConfigurationError
from app.vector_store import SessionVectorStore


class Answer(BaseModel):
    text: str
    grounded: bool = Field(
        description="True if the model answered from the documents; False if it "
        "said the documents do not contain the answer."
    )
    sources: list[RetrievedChunk] = Field(default_factory=list)
    cited_numbers: list[int] = Field(default_factory=list)


def build_llm(settings: Settings) -> BaseChatModel:
    """Create the Gemini chat model. Raises ConfigurationError if no API key."""
    if not settings.has_api_key:
        raise ConfigurationError(
            "No Gemini API key found. Copy .env.example to .env, put your key in "
            "GEMINI_API_KEY, then restart the app."
        )
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.0,
        max_retries=2,
        timeout=60,
    )


def _message_text(message: BaseMessage) -> str:
    content: Any = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # some models return a list of content blocks
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    return str(content)


def _status_code(exc: BaseException) -> int | None:
    for attr in ("code", "status_code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None


def translate_llm_error(exc: BaseException) -> AnswerGenerationError:
    """Turn any Gemini/network exception into a short, friendly message."""
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None and current not in chain and len(chain) < 6:
        chain.append(current)
        current = current.__cause__ or current.__context__

    text = " ".join(str(e) for e in chain).lower()
    codes = {c for c in (_status_code(e) for e in chain) if c}
    names = " ".join(type(e).__name__.lower() for e in chain)

    if 429 in codes or "resource_exhausted" in text or "rate limit" in text or "quota" in text:
        return AnswerGenerationError(
            "Gemini says you have hit a rate limit or quota. Wait a minute and "
            "try again, or check your usage in Google AI Studio."
        )
    if codes & {401, 403} or "api key" in text or "api_key" in text or "permission_denied" in text:
        return AnswerGenerationError(
            "Gemini rejected the API key. Check GEMINI_API_KEY in your .env file."
        )
    if 404 in codes or ("not found" in text and "model" in text):
        return AnswerGenerationError(
            "Gemini could not find the model name in GEMINI_MODEL. Check the "
            "current model names in Google AI Studio and update .env."
        )
    if any(k in names for k in ("connect", "timeout", "network", "ssl")) or any(
        k in text for k in ("connection", "timed out", "name resolution", "network")
    ):
        return AnswerGenerationError(
            "Could not reach Gemini. Check your internet connection and try again."
        )
    if codes & {500, 502, 503, 504}:
        return AnswerGenerationError(
            "Gemini is temporarily unavailable. Please try again in a moment."
        )
    return AnswerGenerationError(
        f"The AI model returned an error ({type(exc).__name__}). Please try again."
    )


class RAGPipeline:
    def __init__(self, store: SessionVectorStore, llm: BaseChatModel, top_k: int) -> None:
        self.store = store
        self.llm = llm
        self.top_k = top_k

    def ask(self, question: str) -> Answer:
        question = question.strip()
        if not question:
            raise ValueError("Question must not be empty.")

        if self.store.count() == 0:
            return Answer(text=NO_DOCUMENTS_MESSAGE, grounded=False)

        chunks = retrieve(self.store, question, self.top_k)
        if not chunks:
            return Answer(text=NO_INFO_MESSAGE, grounded=False)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=USER_PROMPT.format(
                    context=format_context(chunks), question=question
                )
            ),
        ]
        try:
            reply = self.llm.invoke(messages)
        except Exception as exc:  # translate everything into a friendly error
            raise translate_llm_error(exc) from exc

        text = _message_text(reply).strip()
        if not text or text.startswith(INSUFFICIENT_MARKER):
            return Answer(text=NO_INFO_MESSAGE, grounded=False, sources=chunks)

        cited = sorted(
            {int(n) for n in re.findall(r"\[(\d+)\]", text) if 1 <= int(n) <= len(chunks)}
        )
        return Answer(text=text, grounded=True, sources=chunks, cited_numbers=cited)
