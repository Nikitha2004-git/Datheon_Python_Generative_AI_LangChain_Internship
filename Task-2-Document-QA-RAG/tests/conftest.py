"""Shared test helpers: a fake embedding model and tiny PDF builders.

The fake embedder turns words into numbers with a hash, so tests run offline,
instantly, and never download a real model or call a paid API.
"""

from __future__ import annotations

import hashlib
import io
import re
import sys
from pathlib import Path

import pytest
from langchain_core.embeddings import Embeddings
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DIM = 64


class FakeEmbeddings(Embeddings):
    """Bag-of-words hashing embeddings: shared words => similar vectors."""

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * DIM
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM
            vec[idx] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts):
        return [self._embed(t) for t in texts]

    def embed_query(self, text):
        return self._embed(text)


def make_pdf(pages: list[str]) -> bytes:
    """Build a small text PDF. An empty string makes a page with no text."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    for text in pages:
        y = 800
        for line in text.splitlines():
            pdf.drawString(50, y, line)
            y -= 16
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


@pytest.fixture
def embeddings():
    return FakeEmbeddings()


@pytest.fixture
def store(tmp_path, embeddings):
    from app.vector_store import SessionVectorStore

    s = SessionVectorStore("testsession", embeddings, tmp_path / "chroma")
    yield s
    s.delete_permanently()


@pytest.fixture
def pdf_bytes():
    return make_pdf(
        [
            "Solar panels convert sunlight into electricity.",
            "Wind turbines use moving air to generate power.",
        ]
    )
