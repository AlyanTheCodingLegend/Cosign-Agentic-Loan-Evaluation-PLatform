"""Affordability ratios as pure functions. All arithmetic lives here, never in the model."""

from app.models.contract import Metrics

MONTHS_PER_YEAR = 12


class InvalidIncomeError(ValueError):
    """Raised when an income used as a divisor is zero or negative."""


def _require_positive(value: float, name: str) -> None:
    if value <= 0:
        raise InvalidIncomeError(f"{name} must be positive, got {value}")


def loan_to_income(loan_amount: float, annual_income: float) -> float:
    """Return loan amount divided by annual income."""
    _require_positive(annual_income, "annual_income")
    return loan_amount / annual_income


def payment_to_income(annuity: float, annual_income: float) -> float:
    """Return annuity divided by monthly income."""
    _require_positive(annual_income, "annual_income")
    return annuity / (annual_income / MONTHS_PER_YEAR)


def income_mismatch_pct(annual_income: float, document_income: float | None) -> float | None:
    """Return the gap between form and document income as a fraction of document income."""
    _require_positive(annual_income, "annual_income")
    if document_income is None:
        return None
    _require_positive(document_income, "document_income")
    return abs(annual_income - document_income) / document_income


def compute_metrics(
    annual_income: float,
    loan_amount: float,
    annuity: float,
    document_income: float | None,
) -> Metrics:
    """Compute every metric the reasoner and router need."""
    return Metrics(
        loan_to_income=loan_to_income(loan_amount, annual_income),
        payment_to_income=payment_to_income(annuity, annual_income),
        income_mismatch_pct=income_mismatch_pct(annual_income, document_income),
    )
