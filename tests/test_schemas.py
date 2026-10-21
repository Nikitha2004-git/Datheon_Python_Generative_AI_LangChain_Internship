import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas import Invoice, Resume

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

VALID_INVOICE = {
    "vendor_name": "Acme Ltd", "invoice_number": "A-1", "invoice_date": "2024-03-05",
    "total_amount": 100.5, "currency": "USD", "customer_name": None, "tax_amount": None,
}
VALID_RESUME = {
    "full_name": "Jo Smith", "email": "jo.smith@mailbox.org", "phone": "+1 555 0100",
    "skills": ["Python"],
    "education": [{"institution": "X Univ", "degree": "BSc", "field_of_study": None, "graduation_year": 2020}],
    "experience": [{"company": "Y", "job_title": "Dev", "start_date": "2020-01", "end_date": "Present", "description": None}],
}


def test_valid_invoice():
    invoice = Invoice.model_validate(VALID_INVOICE)
    assert str(invoice.invoice_date) == "2024-03-05"
    assert invoice.model_dump(mode="json")["total_amount"] == 100.5


def test_valid_resume():
    resume = Resume.model_validate(VALID_RESUME)
    assert resume.skills == ["Python"] and resume.education[0].graduation_year == 2020


def test_expected_example_outputs_validate():
    Invoice.model_validate(json.loads((EXAMPLES / "expected_invoice_output.json").read_text()))
    Resume.model_validate(json.loads((EXAMPLES / "expected_resume_output.json").read_text()))


def test_zero_is_different_from_missing():
    zero = Invoice.model_validate({**VALID_INVOICE, "total_amount": 0})
    missing = Invoice.model_validate({**VALID_INVOICE, "total_amount": None})
    assert zero.total_amount == 0 and missing.total_amount is None
    assert zero.model_dump(mode="json")["total_amount"] == 0.0
    assert missing.model_dump(mode="json")["total_amount"] is None


@pytest.mark.parametrize(
    "field,bad",
    [
        ("invoice_date", "15/03/2024"),   # not ISO
        ("invoice_date", "2024-02-30"),   # impossible date
        ("total_amount", "abc"),          # not numeric
        ("total_amount", -5),             # negative
        ("total_amount", True),           # boolean is not a number
        ("currency", "usd"),              # must be upper-case ISO
        ("currency", "DOLLARS"),
        ("vendor_name", ""),              # empty string is not "missing"
    ],
)
def test_invalid_invoice_fields(field, bad):
    with pytest.raises(ValidationError):
        Invoice.model_validate({**VALID_INVOICE, field: bad})


def test_invoice_missing_required_key():
    data = copy.deepcopy(VALID_INVOICE)
    del data["total_amount"]
    with pytest.raises(ValidationError):
        Invoice.model_validate(data)


def test_invoice_rejects_extra_keys():
    with pytest.raises(ValidationError):
        Invoice.model_validate({**VALID_INVOICE, "surprise": 1})


@pytest.mark.parametrize("bad", ["not-an-email", "a@", "@b.com", 42])
def test_invalid_email(bad):
    with pytest.raises(ValidationError):
        Resume.model_validate({**VALID_RESUME, "email": bad})


def test_resume_missing_contacts_are_null_and_lists_empty():
    resume = Resume.model_validate(
        {"full_name": None, "email": None, "phone": None, "skills": [], "education": [], "experience": []}
    )
    assert resume.email is None and resume.skills == []


def test_resume_invalid_types():
    with pytest.raises(ValidationError):
        Resume.model_validate({**VALID_RESUME, "skills": "Python"})
    with pytest.raises(ValidationError):
        Resume.model_validate({**VALID_RESUME, "education": [{"institution": "X", "degree": None, "field_of_study": None, "graduation_year": "soon"}]})
    with pytest.raises(ValidationError):
        Resume.model_validate({**VALID_RESUME, "experience": ["Dev at Y"]})
