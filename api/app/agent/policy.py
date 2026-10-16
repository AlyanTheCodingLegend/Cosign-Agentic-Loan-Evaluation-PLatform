"""The explicit risk policy as one pure function, shared by labeling, validation and the fake model.

It is a distilled policy checked against Home Credit outcomes, not real underwriter judgment.
Thresholds live in config.py. See POLICY.md.
"""

from app.config import (
    POLICY_DECLINE_PAYMENT_TO_INCOME,
    POLICY_DECLINE_SCORE_AVERAGE,
    POLICY_REFER_LOAN_TO_INCOME,
    POLICY_REFER_PAYMENT_TO_INCOME,
    POLICY_REFER_SCORE_AVERAGE,
)
from app.models.contract import Recommendation


def score_average(scores: list[float | None]) -> float | None:
    """Mean of the available external scores, or None when all are missing."""
    present = [s for s in scores if s is not None]
    return sum(present) / len(present) if present else None


def classify(
    payment_to_income: float, loan_to_income: float, average_score: float | None
) -> Recommendation:
    """Return approve, refer or decline. Missing scores never approve.

    Payment-to-income and loan-to-income trigger strictly above their limits; the score
    triggers at or below its limit (the bottom percentile band).
    """
    if average_score is None:
        return Recommendation.REFER
    if (
        payment_to_income > POLICY_DECLINE_PAYMENT_TO_INCOME
        or average_score <= POLICY_DECLINE_SCORE_AVERAGE
    ):
        return Recommendation.DECLINE
    if (
        payment_to_income > POLICY_REFER_PAYMENT_TO_INCOME
        or loan_to_income > POLICY_REFER_LOAN_TO_INCOME
        or average_score <= POLICY_REFER_SCORE_AVERAGE
    ):
        return Recommendation.REFER
    return Recommendation.APPROVE
