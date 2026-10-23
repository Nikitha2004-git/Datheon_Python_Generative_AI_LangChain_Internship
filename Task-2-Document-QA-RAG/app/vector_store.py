"""ChromaDB wrapper with one isolated collection per user session."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.utils import collection_name_for


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Chroma rejects None values, so we drop them."""
    return {k: v for k, v in metadata.items() if v is not None}


class SessionVectorStore:
    """Stores chunks for ONE session in its own Chroma collection.

    Because every session gets a different collection name, documents from one
    session can never be retrieved by another.
    """

    def __init__(
        self,
        session_id: str,
        embeddings: Embeddings,
        persist_directory: Path | str | None,
    ) -> None:
        self.session_id = session_id
        self.collection_name = collection_name_for(session_id)
        self._embeddings = embeddings
        self._persist_directory = str(persist_directory) if persist_directory else None
        self._store = self._open()

    def _open(self) -> Chroma:
        return Chroma(
            collection_name=self.collection_name,
            embedding_function=self._embeddings,
            persist_directory=self._persist_directory,
            collection_metadata={"hnsw:space": "cosine"},
        )

    # ---- adding -------------------------------------------------------
    def has_file(self, file_hash: str) -> bool:
        found = self._store.get(where={"file_hash": file_hash}, limit=1)
        return bool(found.get("ids"))

    def add_file_chunks(self, file_hash: str, chunks: list[Document]) -> int:
        """Embed and store chunks. Skips files that are already stored.

        Returns the number of chunks added (0 if the file was already there).
        """
        if not chunks or self.has_file(file_hash):
            return 0
        docs = [
            Document(page_content=c.page_content, metadata=_clean_metadata(c.metadata))
            for c in chunks
        ]
        ids = [c.metadata["chunk_id"] for c in chunks]
        self._store.add_documents(docs, ids=ids)
        return len(docs)

    # ---- reading ------------------------------------------------------
    def count(self) -> int:
        return self._store._collection.count()

    def search(self, query: str, k: int) -> list[tuple[Document, float]]:
        """Return (chunk, distance) pairs; smaller distance = more similar."""
        if self.count() == 0 or not query.strip():
            return []
        k = max(1, min(k, self.count()))
        return self._store.similarity_search_with_score(query, k=k)

    # ---- removing -----------------------------------------------------
    def remove_file(self, file_hash: str) -> None:
        found = self._store.get(where={"file_hash": file_hash})
        ids = found.get("ids") or []
        if ids:
            self._store.delete(ids=ids)

    def clear(self) -> None:
        """Delete the whole collection (all documents of this session)."""
        try:
            self._store.delete_collection()
        except Exception:
            pass  # collection may already be gone
        self._store = self._open()  # fresh, empty collection ready for reuse

    def delete_permanently(self) -> None:
        """Delete the collection and leave nothing behind."""
        try:
            self._store.delete_collection()
        except Exception:
            pass


def purge_persist_directory(persist_directory: Path | str) -> int:
    """Delete every collection in a Chroma directory. Returns how many."""
    path = Path(persist_directory)
    if not path.exists():
        return 0
    client = chromadb.PersistentClient(path=str(path))
    names = [c.name if hasattr(c, "name") else str(c) for c in client.list_collections()]
    for name in names:
        client.delete_collection(name)
    return len(names)
