"""Embedding model loader.

An *embedding model* turns text into a list of numbers (a vector). Texts with
similar meaning get vectors that are close together. We use a small
sentence-transformers model that runs locally on your CPU - no API key needed.
The first run downloads the model (about 90 MB) from Hugging Face; after that
it is cached on your computer and works offline.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.utils import ConfigurationError


@lru_cache(maxsize=2)
def get_embeddings(model_name: str) -> Embeddings:
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as exc:  # pragma: no cover - depends on install
        raise ConfigurationError(
            "Embedding packages are missing. Run: pip install -r requirements.txt"
        ) from exc
    try:
        return HuggingFaceEmbeddings(
            model_name=model_name,
            encode_kwargs={"normalize_embeddings": True},
        )
    except Exception as exc:
        raise ConfigurationError(
            f"Could not load the embedding model '{model_name}'. The first run "
            "needs an internet connection to download it. "
            f"Details: {type(exc).__name__}"
        ) from exc
