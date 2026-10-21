import pytest

from app.errors import InputError, ResponseFormatError, SchemaValidationError
from app.schemas import Invoice
from app.validators import decode_uploaded_file, parse_json_response, validate_data

GOOD = {
    "vendor_name": "A", "invoice_number": "1", "invoice_date": "2024-01-02",
    "total_amount": 1, "currency": "EUR", "customer_name": None, "tax_amount": None,
}


def test_parse_valid_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}


@pytest.mark.parametrize("raw", ["{bad json", "", "   ", None, '{"a": 1,}', "```json\n{}\n```", "[1, 2]", '"text"'])
def test_parse_rejects_bad_responses(raw):
    with pytest.raises(ResponseFormatError):
        parse_json_response(raw)


def test_validate_data_ok():
    assert validate_data(Invoice, GOOD).currency == "EUR"


def test_validate_data_errors_are_readable_and_hide_input():
    with pytest.raises(SchemaValidationError) as info:
        validate_data(Invoice, {**GOOD, "invoice_date": "yesterday", "total_amount": -1})
    assert "could not be validated" in info.value.user_message
    joined = " ".join(info.value.details)
    assert "invoice_date" in joined and "total_amount" in joined and "yesterday" not in joined


def test_decode_valid_file(tmp_path):
    path = tmp_path / "doc.txt"
    path.write_text("Hello invoice", encoding="utf-8")
    assert decode_uploaded_file(path.name, path.read_bytes(), 1000) == "Hello invoice"


@pytest.mark.parametrize(
    "name,raw,limit",
    [
        ("doc.pdf", b"text", 1000),         # wrong extension
        ("noext", b"text", 1000),
        ("doc.txt", b"", 1000),             # empty
        ("doc.txt", b"   \n ", 1000),       # whitespace only
        ("doc.txt", b"x" * 11, 10),         # too large
        ("doc.txt", b"\xff\xfe\x00bad", 1000),  # not UTF-8 text
        ("doc.txt", b"abc\x00def", 1000),   # binary content
    ],
)
def test_decode_rejects_bad_files(name, raw, limit):
    with pytest.raises(InputError):
        decode_uploaded_file(name, raw, limit)
