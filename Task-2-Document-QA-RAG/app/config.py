"""Central configuration.

All settings come from environment variables (loaded from a local ``.env``
file). Nothing secret is ever hard-coded here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

PLACEHOLDER_KEYS = {"", "your_gemini_api_key_here", "changeme", "your_api_key"}


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= minimum else default


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    max_file_size_mb: int
    chroma_dir: Path

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def has_api_key(self) -> bool:
        return self.gemini_api_key.strip().lower() not in PLACEHOLDER_KEYS


def load_settings() -> Settings:
    chunk_size = _int_env("CHUNK_SIZE", 1000, minimum=100)
    overlap = _int_env("CHUNK_OVERLAP", 150, minimum=0)
    if overlap >= chunk_size:  # overlap must be smaller than the chunk
        overlap = max(0, chunk_size // 5)
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
        or "gemini-3.5-flash-lite",
        embedding_model=os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ).strip(),
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        top_k=_int_env("TOP_K", 4),
        max_file_size_mb=_int_env("MAX_FILE_SIZE_MB", 10),
        chroma_dir=PROJECT_ROOT / os.getenv("CHROMA_DIR", "chroma_db"),
    )
