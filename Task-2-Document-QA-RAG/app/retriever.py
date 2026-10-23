"""Find the chunks most relevant to a question."""

from __future__ import annotations

from pydantic import BaseModel

from app.vector_store import SessionVectorStore


class RetrievedChunk(BaseModel):
    text: str
    source: str
    page: int | None = None
    chunk_index: int | None = None
    distance: float  # cosine distance: 0 = identical meaning, bigger = less similar

    @property
    def label(self) -> str:
        if self.page is not None:
            return f"{self.source} (page {self.page})"
        return self.source


def retrieve(store: SessionVectorStore, question: str, top_k: int) -> list[RetrievedChunk]:
    """Return up to ``top_k`` chunks, best match first. Empty list if none."""
    results = store.search(question, k=top_k)
    chunks: list[RetrievedChunk] = []
    for doc, distance in results:
        meta = doc.metadata or {}
        chunks.append(
            RetrievedChunk(
                text=doc.page_content,
                source=str(meta.get("source", "unknown")),
                page=meta.get("page"),
                chunk_index=meta.get("chunk_index"),
                distance=float(distance),
            )
        )
    chunks.sort(key=lambda c: c.distance)
    return chunks
