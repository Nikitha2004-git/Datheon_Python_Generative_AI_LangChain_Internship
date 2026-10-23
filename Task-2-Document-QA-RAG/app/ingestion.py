"""Glue between loading, splitting, embedding and storing uploaded files."""

from __future__ import annotations

from dataclasses import dataclass

from app.document_loader import load_file
from app.text_splitter import split_documents
from app.utils import DocumentLoadError, DocumentQAError
from app.vector_store import SessionVectorStore


@dataclass
class IngestResult:
    filename: str
    status: str  # "added" | "skipped" | "error"
    message: str
    file_hash: str | None = None
    pages: int = 0
    chunks: int = 0
    size_bytes: int = 0


def ingest_file(
    store: SessionVectorStore,
    filename: str,
    data: bytes,
    max_bytes: int,
    chunk_size: int,
    chunk_overlap: int,
) -> IngestResult:
    """Process one uploaded file. Never raises for bad files - returns a status."""
    try:
        loaded = load_file(filename, data, max_bytes)
    except DocumentLoadError as exc:
        return IngestResult(filename, "error", str(exc), size_bytes=len(data))

    if store.has_file(loaded.file_hash):
        return IngestResult(
            filename,
            "skipped",
            "Already processed - no need to embed it again.",
            file_hash=loaded.file_hash,
            pages=len(loaded.pages),
            size_bytes=len(data),
        )
    try:
        chunks = split_documents(loaded.pages, chunk_size, chunk_overlap)
        added = store.add_file_chunks(loaded.file_hash, chunks)
    except DocumentQAError as exc:
        return IngestResult(filename, "error", str(exc), size_bytes=len(data))
    except Exception as exc:  # embedding/database problems
        return IngestResult(
            filename,
            "error",
            f"Could not store '{filename}' ({type(exc).__name__}). "
            "Check that the embedding model could be downloaded/loaded.",
            size_bytes=len(data),
        )
    return IngestResult(
        filename,
        "added",
        f"Processed {len(loaded.pages)} page(s) into {added} chunk(s).",
        file_hash=loaded.file_hash,
        pages=len(loaded.pages),
        chunks=added,
        size_bytes=len(data),
    )
