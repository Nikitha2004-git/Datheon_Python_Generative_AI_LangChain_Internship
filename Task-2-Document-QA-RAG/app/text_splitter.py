"""Split page text into overlapping chunks that keep their metadata."""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(
    pages: list[Document], chunk_size: int, chunk_overlap: int
) -> list[Document]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(pages)  # metadata is copied to each chunk

    counters: dict[str, int] = {}
    for chunk in chunks:
        key = f"{chunk.metadata.get('file_hash')}"
        index = counters.get(key, 0)
        counters[key] = index + 1
        chunk.metadata["chunk_index"] = index
        chunk.metadata["chunk_id"] = f"{key[:16]}-{index}"
    return chunks
