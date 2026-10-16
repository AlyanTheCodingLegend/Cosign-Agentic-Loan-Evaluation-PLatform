import pytest

from app import config
from app.agent.policy import classify, score_average
from app.models.contract import Recommendation

GOOD = 0.6


def test_healthy_case_is_approved() -> None:
    assert classify(1.5, 3.0, GOOD) is Recommendation.APPROVE


def test_missing_scores_never_approve() -> None:
    assert classify(0.1, 1.0, None) is Recommendation.REFER


def test_payment_to_income_above_decline_limit_declines() -> None:
    over = config.POLICY_DECLINE_PAYMENT_TO_INCOME + 0.01
    assert classify(over, 3.0, GOOD) is Recommendation.DECLINE


def test_payment_to_income_exactly_at_decline_limit_only_refers() -> None:
    at = config.POLICY_DECLINE_PAYMENT_TO_INCOME
    assert classify(at, 3.0, GOOD) is Recommendation.REFER


def test_payment_to_income_exactly_at_refer_limit_approves() -> None:
    at = config.POLICY_REFER_PAYMENT_TO_INCOME
    assert classify(at, 3.0, GOOD) is Recommendation.APPROVE


def test_payment_to_income_in_band_refers() -> None:
    assert classify(config.POLICY_REFER_PAYMENT_TO_INCOME + 0.01, 3.0, GOOD) is Recommendation.REFER


@pytest.mark.parametrize("lti", [config.POLICY_REFER_LOAN_TO_INCOME + 0.01, 50.0])
def test_loan_to_income_only_ever_refers(lti: float) -> None:
    assert classify(1.0, lti, GOOD) is Recommendation.REFER


def test_score_at_decline_limit_declines() -> None:
    assert classify(1.0, 3.0, config.POLICY_DECLINE_SCORE_AVERAGE) is Recommendation.DECLINE


def test_score_at_refer_limit_refers() -> None:
    assert classify(1.0, 3.0, config.POLICY_REFER_SCORE_AVERAGE) is Recommendation.REFER


def test_score_just_above_refer_limit_approves() -> None:
    assert classify(1.0, 3.0, config.POLICY_REFER_SCORE_AVERAGE + 0.01) is Recommendation.APPROVE


def test_limits_are_ordered() -> None:
    assert config.POLICY_REFER_PAYMENT_TO_INCOME < config.POLICY_DECLINE_PAYMENT_TO_INCOME
    assert config.POLICY_DECLINE_SCORE_AVERAGE < config.POLICY_REFER_SCORE_AVERAGE


def test_score_average_ignores_missing() -> None:
    assert score_average([0.2, None, 0.4]) == pytest.approx(0.3)
    assert score_average([None, None, None]) is None
