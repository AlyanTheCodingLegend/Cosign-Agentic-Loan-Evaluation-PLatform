import pytest

from app.agent.metrics import (
    InvalidIncomeError,
    compute_metrics,
    income_mismatch_pct,
    loan_to_income,
    payment_to_income,
)

# --- normal values ---


def test_loan_to_income() -> None:
    assert loan_to_income(300_000.0, 120_000.0) == pytest.approx(2.5)


def test_payment_to_income_uses_monthly_income() -> None:
    # 18,000 / (120,000 / 12) = 18,000 / 10,000
    assert payment_to_income(18_000.0, 120_000.0) == pytest.approx(1.8)


@pytest.mark.parametrize(
    ("annual", "document", "expected"),
    [
        pytest.param(110_000.0, 100_000.0, 0.10, id="form-above-document"),
        pytest.param(90_000.0, 100_000.0, 0.10, id="form-below-document"),
        pytest.param(100_000.0, 100_000.0, 0.0, id="equal"),
        pytest.param(150_000.0, 100_000.0, 0.50, id="large-gap"),
    ],
)
def test_income_mismatch_pct(annual: float, document: float, expected: float) -> None:
    assert income_mismatch_pct(annual, document) == pytest.approx(expected)


def test_compute_metrics_assembles_all_values() -> None:
    metrics = compute_metrics(
        annual_income=120_000.0, loan_amount=300_000.0, annuity=18_000.0, document_income=100_000.0
    )
    assert metrics.loan_to_income == pytest.approx(2.5)
    assert metrics.payment_to_income == pytest.approx(1.8)
    assert metrics.income_mismatch_pct == pytest.approx(0.2)


# --- missing document income ---


def test_mismatch_is_none_without_document_income() -> None:
    assert income_mismatch_pct(120_000.0, None) is None


def test_compute_metrics_without_document_income() -> None:
    metrics = compute_metrics(
        annual_income=120_000.0, loan_amount=300_000.0, annuity=18_000.0, document_income=None
    )
    assert metrics.income_mismatch_pct is None


# --- zero and negative income ---


@pytest.mark.parametrize("income", [0.0, -1.0, -120_000.0])
def test_loan_to_income_rejects_non_positive_income(income: float) -> None:
    with pytest.raises(InvalidIncomeError, match="annual_income"):
        loan_to_income(300_000.0, income)


@pytest.mark.parametrize("income", [0.0, -1.0, -120_000.0])
def test_payment_to_income_rejects_non_positive_income(income: float) -> None:
    with pytest.raises(InvalidIncomeError, match="annual_income"):
        payment_to_income(18_000.0, income)


@pytest.mark.parametrize("income", [0.0, -1.0])
def test_mismatch_rejects_non_positive_annual_income(income: float) -> None:
    with pytest.raises(InvalidIncomeError, match="annual_income"):
        income_mismatch_pct(income, 100_000.0)


@pytest.mark.parametrize("income", [0.0, -1.0])
def test_mismatch_rejects_non_positive_document_income(income: float) -> None:
    with pytest.raises(InvalidIncomeError, match="document_income"):
        income_mismatch_pct(120_000.0, income)


def test_compute_metrics_rejects_zero_income() -> None:
    with pytest.raises(InvalidIncomeError):
        compute_metrics(
            annual_income=0.0, loan_amount=300_000.0, annuity=18_000.0, document_income=None
        )
