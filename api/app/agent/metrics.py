"""Affordability ratios as pure functions. All arithmetic lives here, never in the model."""

from app.models.contract import ApplicantFields, Metrics


def payment_to_income(annuity: float, annual_income: float) -> float:
    """Return annuity divided by monthly income."""
    raise NotImplementedError


def compute_metrics(fields: ApplicantFields) -> Metrics:
    """Compute every metric the reasoner and router need. Call only after check_completeness."""
    raise NotImplementedError
