"""JSON parsing, Pydantic validation, and safe file decoding."""

from __future__ import annotations

import json
from pathlib import PurePath
from typing import Any

from pydantic import BaseModel, ValidationError

from app.errors import InputError, ResponseFormatError, SchemaValidationError

VALIDATION_FAILED_MESSAGE = (
    "The AI response could not be validated. Please review the input or try again."
)


def parse_json_response(raw: object) -> dict[str, Any]:
    """Parse the model output with json.loads. No repairing, no regex tricks.

    Anything that is not a JSON object (for example Markdown-wrapped JSON or a
    list) is rejected.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ResponseFormatError(
            "The AI returned an empty or unexpected response. Please try again."
        )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ResponseFormatError(
            "The AI response was not valid JSON. Please try again.",
            [f"JSON error at line {exc.lineno}, column {exc.colno}: {exc.msg}"],
        ) from None
    if not isinstance(data, dict):
        raise ResponseFormatError(
            "The AI response was JSON, but not a JSON object. Please try again."
        )
    return data


def format_validation_errors(error: ValidationError) -> list[str]:
    """Turn a Pydantic error into short readable lines (no input values)."""
    lines = []
    for item in error.errors(include_input=False, include_url=False):
        location = ".".join(str(part) for part in item["loc"]) or "(root)"
        lines.append(f"{location}: {item['msg']}")
    return lines


def validate_data(model_class: type[BaseModel], data: dict[str, Any]) -> BaseModel:
    """Validate `data`, then validate the model's own JSON output a second time.

    The second pass guarantees that what we display and let the user download
    is itself valid.
    """
    try:
        model = model_class.model_validate(data)
        return model_class.model_validate(model.model_dump(mode="json"))
    except ValidationError as exc:
        raise SchemaValidationError(
            VALIDATION_FAILED_MESSAGE, format_validation_errors(exc)
        ) from None


def decode_uploaded_file(filename: str, raw: bytes, max_bytes: int) -> str:
    """Safely turn an uploaded .txt file into text. The content is never executed."""
    if PurePath(filename or "").suffix.lower() != ".txt":
        raise InputError("Unsupported file format. Please upload a .txt file.")
    if not raw:
        raise InputError("The uploaded file is empty.")
    if len(raw) > max_bytes:
        raise InputError(
            f"The file is too large. The limit is {max_bytes // 1000} KB."
        )
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise InputError(
            "The file could not be read as UTF-8 text. Please save it as plain text."
        ) from None
    if "\x00" in text:
        raise InputError("The file does not look like plain text.")
    if not text.strip():
        raise InputError("The uploaded file contains only whitespace.")
    return text
