"""Pydantic models describing the JSON we expect for each document type.

Every field must be PRESENT in the AI output. Unknown scalar values must be
`null`; unknown collections must be `[]`. Extra keys are rejected.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_serializer,
    field_validator,
)

Money = Annotated[Decimal, Field(ge=0, allow_inf_nan=False, max_digits=18)]


def _reject_bool(value: object) -> object:
    """True/False would otherwise be silently accepted as 1/0."""
    if isinstance(value, bool):
        raise ValueError("must be a number, not true/false")
    return value


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Invoice(_StrictModel):
    vendor_name: str | None = Field(min_length=1)
    invoice_number: str | None = Field(min_length=1)
    invoice_date: date | None  # ISO 8601: YYYY-MM-DD
    total_amount: Money | None  # 0 is a real zero; null means "not found"
    currency: str | None = Field(pattern=r"^[A-Z]{3}$")  # ISO 4217, e.g. USD
    customer_name: str | None = Field(min_length=1)
    tax_amount: Money | None

    @field_validator("total_amount", "tax_amount", mode="before")
    @classmethod
    def _numbers_only(cls, value: object) -> object:
        return _reject_bool(value)

    @field_serializer("total_amount", "tax_amount", when_used="json")
    def _money_as_number(self, value: Decimal | None) -> float | None:
        return None if value is None else float(value)


class Education(_StrictModel):
    institution: str | None = Field(min_length=1)
    degree: str | None = Field(min_length=1)
    field_of_study: str | None = Field(min_length=1)
    graduation_year: int | None = Field(ge=1950, le=2100)

    @field_validator("graduation_year", mode="before")
    @classmethod
    def _year_not_bool(cls, value: object) -> object:
        return _reject_bool(value)


class Experience(_StrictModel):
    company: str | None = Field(min_length=1)
    job_title: str | None = Field(min_length=1)
    start_date: str | None = Field(min_length=1)  # as written, e.g. "2021-06"
    end_date: str | None = Field(min_length=1)  # e.g. "2023-08" or "Present"
    description: str | None = Field(min_length=1)


class Resume(_StrictModel):
    full_name: str | None = Field(min_length=1)
    email: EmailStr | None
    phone: str | None = Field(min_length=3)
    skills: list[Annotated[str, Field(min_length=1)]]
    education: list[Education]
    experience: list[Experience]
