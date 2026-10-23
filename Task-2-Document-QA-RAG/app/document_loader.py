"""Read PDF and TXT files into page-level text with metadata."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.utils import DocumentLoadError, file_hash

ALLOWED_EXTENSIONS = {".pdf", ".txt"}


@dataclass(frozen=True)
class LoadedFile:
    filename: str
    file_hash: str
    pages: list[Document]  # one Document per PDF page (or one for a TXT file)


def validate_upload(filename: str, data: bytes, max_bytes: int) -> str:
    """Check extension, emptiness and size. Returns the lowercase extension."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise DocumentLoadError(
            f"'{filename}' is not supported. Please upload a PDF or TXT file."
        )
    if len(data) == 0:
        raise DocumentLoadError(f"'{filename}' is empty (0 bytes).")
    if len(data) > max_bytes:
        limit_mb = max_bytes / (1024 * 1024)
        raise DocumentLoadError(
            f"'{filename}' is larger than the {limit_mb:g} MB limit."
        )
    return ext


def _decode_text(filename: str, data: bytes) -> str:
    """Decode text bytes. UTF-16 is only trusted when a byte-order mark exists
    (otherwise random bytes would "decode" into nonsense)."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode("utf-16")
        except UnicodeError:
            pass
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeError:
            continue
    raise DocumentLoadError(f"'{filename}' could not be decoded as text.")


def _load_txt(filename: str, data: bytes, digest: str) -> LoadedFile:
    text = _decode_text(filename, data)
    if "\x00" in text:
        raise DocumentLoadError(
            f"'{filename}' looks like a binary file, not plain text."
        )
    if not text.strip():
        raise DocumentLoadError(f"'{filename}' contains no readable text.")
    page = Document(
        page_content=text,
        metadata={"source": filename, "page": None, "file_hash": digest},
    )
    return LoadedFile(filename, digest, [page])


def _load_pdf(filename: str, data: bytes, digest: str) -> LoadedFile:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            # Many "encrypted" PDFs open with an empty password.
            if not reader.decrypt(""):
                raise DocumentLoadError(
                    f"'{filename}' is password-protected and cannot be read."
                )
        pages: list[Document] = []
        for number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": filename,
                            "page": number,
                            "file_hash": digest,
                        },
                    )
                )
    except DocumentLoadError:
        raise
    except (PyPdfError, ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        raise DocumentLoadError(
            f"'{filename}' could not be read. The PDF may be corrupted."
        ) from exc
    except Exception as exc:  # pypdf can raise odd errors on broken files
        raise DocumentLoadError(
            f"'{filename}' could not be read. The PDF may be corrupted."
        ) from exc

    if not pages:
        raise DocumentLoadError(
            f"No extractable text found in '{filename}'. It may be a scanned "
            "PDF (images of pages). Scanned PDFs need OCR, which this app does "
            "not include."
        )
    return LoadedFile(filename, digest, pages)


def load_file(filename: str, data: bytes, max_bytes: int) -> LoadedFile:
    """Validate and read one uploaded file. Raises DocumentLoadError on problems."""
    ext = validate_upload(filename, data, max_bytes)
    digest = file_hash(data)
    if ext == ".txt":
        return _load_txt(filename, data, digest)
    return _load_pdf(filename, data, digest)
