"""The extraction workflow: input check -> prompt -> AI -> parse -> validate."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.errors import InputError
from app.llm_client import LLMClient
from app.prompt_templates import DOCUMENT_SPECS, SYSTEM_INSTRUCTION, DocumentSpec, build_prompt
from app.validators import parse_json_response, validate_data

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractionResult:
    """Only ever created after parsing AND validation both succeeded."""

    document_type: str
    data: dict[str, Any]
    json_text: str


def get_spec(document_type: str) -> DocumentSpec:
    try:
        return DOCUMENT_SPECS[document_type]
    except KeyError:
        raise InputError(f"Unsupported document type: {document_type!r}.") from None


def validate_input_text(text: str | None, max_chars: int) -> str:
    """Return the stripped text or raise a friendly InputError."""
    if text is None or not text.strip():
        raise InputError("Please enter some document text before extracting.")
    cleaned = text.strip()
    if len(cleaned) > max_chars:
        raise InputError(
            f"The document is too long ({len(cleaned):,} characters). "
            f"The limit is {max_chars:,}."
        )
    return cleaned


def extract_document(
    document_type: str, text: str | None, client: LLMClient, max_chars: int = 20_000
) -> ExtractionResult:
    spec = get_spec(document_type)
    cleaned = validate_input_text(text, max_chars)
    prompt = build_prompt(spec, cleaned)
    logger.info("Extracting %s (%d characters)", document_type, len(cleaned))
    raw = client.generate_json(SYSTEM_INSTRUCTION, prompt)
    parsed = parse_json_response(raw)
    model = validate_data(spec.model, parsed)
    data = model.model_dump(mode="json")
    return ExtractionResult(document_type, data, json.dumps(data, indent=2))
