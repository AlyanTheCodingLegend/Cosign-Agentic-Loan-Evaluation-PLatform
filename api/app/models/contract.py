"""Shared contract models: applicant fields, metrics, reasoner input and reasoner output."""

from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Fields without which the application cannot be assessed. Missing any of them -> needs_info.
REQUIRED_FIELDS: tuple[str, ...] = ("annual_income", "loan_amount", "annuity", "goods_price")


class Recommendation(StrEnum):
    """What the reasoner recommends."""

    APPROVE = "approve"
    DECLINE = "decline"
    REFER = "refer"


class ApplicantFields(BaseModel):
    """Structured applicant fields produced by extraction. Any value may be missing (None).

    Unknown fields are rejected so protected attributes cannot ride along (hard rule 4).
    """

    model_config = ConfigDict(extra="forbid")

    annual_income: float | None = Field(default=None, gt=0)
    loan_amount: float | None = Field(default=None, gt=0)
    annuity: float | None = Field(default=None, gt=0)
    goods_price: float | None = Field(default=None, gt=0)
    years_employed: float | None = Field(default=None, ge=0)
    ext_source_1: float | None = Field(default=None, ge=0, le=1)
    ext_source_2: float | None = Field(default=None, ge=0, le=1)
    ext_source_3: float | None = Field(default=None, ge=0, le=1)
    stated_income_source: Literal["form", "document"]


class Metrics(BaseModel):
    """Affordability metrics computed in code by metrics.py, never by the model."""

    model_config = ConfigDict(extra="forbid")

    loan_to_income: float = Field(ge=0)
    payment_to_income: float = Field(ge=0)
    # Fraction, not percent: 0.10 means 10%. None when there is only one income source.
    income_mismatch_pct: float | None = Field(default=None, ge=0)


class ReasonerInput(BaseModel):
    """Everything the reasoner sees. Required fields must be present (safety net)."""

    model_config = ConfigDict(extra="forbid")

    fields: ApplicantFields
    metrics: Metrics

    @model_validator(mode="after")
    def _require_complete_fields(self) -> Self:
        missing = [name for name in REQUIRED_FIELDS if getattr(self.fields, name) is None]
        if missing:
            raise ValueError(f"missing required fields: {', '.join(missing)}")
        return self


class ReasonerOutput(BaseModel):
    """Validated output of the reasoner."""

    recommendation: Recommendation
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(min_length=1)
    needs_human: bool
    human_question: str | None

    @model_validator(mode="after")
    def _check_human_flags(self) -> Self:
        if self.recommendation is not Recommendation.APPROVE and not self.needs_human:
            raise ValueError("needs_human must be true when recommendation is not approve")
        if not self.needs_human and self.human_question is not None:
            raise ValueError("human_question must be null when needs_human is false")
        return self
