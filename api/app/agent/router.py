"""Routing rules as pure functions. The model recommends; these rules decide the path."""

from dataclasses import dataclass

from app.config import HIGH_LOAN_AMOUNT_CUTOFF, INCOME_MISMATCH_TOLERANCE, MIN_AUTO_CLEAR_CONFIDENCE
from app.models.contract import (
    REQUIRED_FIELDS,
    ApplicantFields,
    ReasonerInput,
    ReasonerOutput,
    Recommendation,
)
from app.models.status import Status


@dataclass(frozen=True)
class RouteResult:
    """Where the application goes next, and the question for the applicant if any."""

    status: Status
    human_question: str | None = None


def check_completeness(fields: ApplicantFields) -> list[str]:
    """Return the names of missing required fields in REQUIRED_FIELDS order; empty if complete."""
    return [name for name in REQUIRED_FIELDS if getattr(fields, name) is None]


def _require(value: float | None, name: str) -> float:
    # ReasonerInput already rejects missing required fields; this only narrows the type.
    if value is None:
        raise ValueError(f"{name} is missing; ReasonerInput validation was bypassed")
    return value


def _format_income(value: float | None) -> str:
    return "unknown" if value is None else f"{value:,.2f}"


def _income_mismatch_question(fields: ApplicantFields) -> str:
    return (
        f"The income on your form ({_format_income(fields.annual_income)}) differs from the "
        f"income on your document ({_format_income(fields.document_income)}). "
        "Which figure is correct?"
    )


def route(inp: ReasonerInput, output: ReasonerOutput) -> RouteResult:
    """Apply the router rules in the order listed in CLAUDE.md. Thresholds trigger strictly.

    Missing required fields never reach here: check_completeness runs right after extraction.
    """
    mismatch = inp.metrics.income_mismatch_pct
    if mismatch is not None and mismatch > INCOME_MISMATCH_TOLERANCE:
        return RouteResult(Status.NEEDS_INFO, _income_mismatch_question(inp.fields))
    if _require(inp.fields.loan_amount, "loan_amount") > HIGH_LOAN_AMOUNT_CUTOFF:
        return RouteResult(Status.PENDING_REVIEW)
    if output.recommendation in (Recommendation.DECLINE, Recommendation.REFER):
        return RouteResult(Status.PENDING_REVIEW)
    if output.needs_human:
        return RouteResult(Status.PENDING_REVIEW)
    if output.confidence < MIN_AUTO_CLEAR_CONFIDENCE:
        return RouteResult(Status.PENDING_REVIEW)
    return RouteResult(Status.AUTO_CLEARED)
