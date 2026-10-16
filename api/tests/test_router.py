import itertools
import math

import pytest

from app.agent.router import RouteResult, check_completeness, route
from app.config import HIGH_LOAN_AMOUNT_CUTOFF, INCOME_MISMATCH_TOLERANCE, MIN_AUTO_CLEAR_CONFIDENCE
from app.models.contract import (
    REQUIRED_FIELDS,
    ApplicantFields,
    Metrics,
    ReasonerInput,
    ReasonerOutput,
)
from app.models.status import Status

SMALL_LOAN = HIGH_LOAN_AMOUNT_CUTOFF / 10
HIGH_CONFIDENCE = 0.99


def above(x: float) -> float:
    return math.nextafter(x, math.inf)


def below(x: float) -> float:
    return math.nextafter(x, -math.inf)


def make_input(
    *,
    loan_amount: float = SMALL_LOAN,
    mismatch: float | None = 0.0,
    annual_income: float = 120_000.0,
    document_income: float | None = 120_000.0,
) -> ReasonerInput:
    fields = ApplicantFields(
        annual_income=annual_income,
        document_income=document_income,
        loan_amount=loan_amount,
        annuity=18_000.0,
        goods_price=loan_amount,
    )
    metrics = Metrics(loan_to_income=2.5, payment_to_income=0.18, income_mismatch_pct=mismatch)
    return ReasonerInput(fields=fields, metrics=metrics)


def make_output(
    *,
    recommendation: str = "approve",
    confidence: float = HIGH_CONFIDENCE,
    needs_human: bool = False,
) -> ReasonerOutput:
    return ReasonerOutput.model_validate(
        {
            "recommendation": recommendation,
            "confidence": confidence,
            "reasons": ["payment_to_income 0.18 is below the limit"],
            "needs_human": needs_human,
            "human_question": None,
        }
    )


# --- check_completeness ---


def test_complete_fields_report_nothing_missing(complete_fields: dict[str, object]) -> None:
    assert check_completeness(ApplicantFields.model_validate(complete_fields)) == []


@pytest.mark.parametrize("missing", REQUIRED_FIELDS)
def test_one_missing_field_is_reported(complete_fields: dict[str, object], missing: str) -> None:
    fields = ApplicantFields.model_validate({**complete_fields, missing: None})
    assert check_completeness(fields) == [missing]


def test_all_missing_fields_reported_in_order() -> None:
    assert check_completeness(ApplicantFields()) == [
        "annual_income",
        "loan_amount",
        "annuity",
        "goods_price",
    ]


def test_optional_fields_do_not_count_as_missing(complete_fields: dict[str, object]) -> None:
    optional_nulls = {
        "document_income": None,
        "years_employed": None,
        "ext_source_1": None,
        "ext_source_2": None,
        "ext_source_3": None,
    }
    fields = ApplicantFields.model_validate({**complete_fields, **optional_nulls})
    assert check_completeness(fields) == []


# --- each rule on its own ---


def test_clean_case_auto_clears() -> None:
    assert route(make_input(), make_output()) == RouteResult(Status.AUTO_CLEARED)


def test_rule_1_income_mismatch_needs_info_with_both_figures() -> None:
    inp = make_input(mismatch=0.25, annual_income=150_000.0, document_income=120_000.0)
    result = route(inp, make_output())
    assert result.status is Status.NEEDS_INFO
    assert result.human_question is not None
    assert "150,000.00" in result.human_question
    assert "120,000.00" in result.human_question


def test_rule_2_high_loan_amount_pending_review() -> None:
    result = route(make_input(loan_amount=HIGH_LOAN_AMOUNT_CUTOFF * 2), make_output())
    assert result == RouteResult(Status.PENDING_REVIEW)


@pytest.mark.parametrize("recommendation", ["decline", "refer"])
def test_rule_3_decline_or_refer_pending_review(recommendation: str) -> None:
    output = make_output(recommendation=recommendation, needs_human=True)
    assert route(make_input(), output) == RouteResult(Status.PENDING_REVIEW)


def test_rule_4_needs_human_pending_review() -> None:
    assert route(make_input(), make_output(needs_human=True)) == RouteResult(Status.PENDING_REVIEW)


def test_rule_5_low_confidence_pending_review() -> None:
    result = route(make_input(), make_output(confidence=0.1))
    assert result == RouteResult(Status.PENDING_REVIEW)


def test_missing_mismatch_never_triggers_rule_1() -> None:
    result = route(make_input(mismatch=None, document_income=None), make_output())
    assert result.status is Status.AUTO_CLEARED


# --- exact boundaries: thresholds trigger strictly ---


@pytest.mark.parametrize(
    ("mismatch", "expected"),
    [
        pytest.param(below(INCOME_MISMATCH_TOLERANCE), Status.AUTO_CLEARED, id="just-below"),
        pytest.param(INCOME_MISMATCH_TOLERANCE, Status.AUTO_CLEARED, id="exactly-at"),
        pytest.param(above(INCOME_MISMATCH_TOLERANCE), Status.NEEDS_INFO, id="just-above"),
    ],
)
def test_mismatch_tolerance_boundary(mismatch: float, expected: Status) -> None:
    assert route(make_input(mismatch=mismatch), make_output()).status is expected


@pytest.mark.parametrize(
    ("loan_amount", "expected"),
    [
        pytest.param(below(HIGH_LOAN_AMOUNT_CUTOFF), Status.AUTO_CLEARED, id="just-below"),
        pytest.param(HIGH_LOAN_AMOUNT_CUTOFF, Status.AUTO_CLEARED, id="exactly-at"),
        pytest.param(above(HIGH_LOAN_AMOUNT_CUTOFF), Status.PENDING_REVIEW, id="just-above"),
    ],
)
def test_high_loan_amount_boundary(loan_amount: float, expected: Status) -> None:
    assert route(make_input(loan_amount=loan_amount), make_output()).status is expected


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        pytest.param(below(MIN_AUTO_CLEAR_CONFIDENCE), Status.PENDING_REVIEW, id="just-below"),
        pytest.param(MIN_AUTO_CLEAR_CONFIDENCE, Status.AUTO_CLEARED, id="exactly-at"),
        pytest.param(above(MIN_AUTO_CLEAR_CONFIDENCE), Status.AUTO_CLEARED, id="just-above"),
    ],
)
def test_confidence_boundary(confidence: float, expected: Status) -> None:
    assert route(make_input(), make_output(confidence=confidence)).status is expected


def test_approve_with_needs_human_and_high_confidence_goes_to_review() -> None:
    output = make_output(confidence=1.0, needs_human=True)
    assert route(make_input(), output) == RouteResult(Status.PENDING_REVIEW)


# --- precedence ---


def test_mismatch_beats_high_loan_amount() -> None:
    inp = make_input(mismatch=0.5, loan_amount=HIGH_LOAN_AMOUNT_CUTOFF * 2)
    assert route(inp, make_output()).status is Status.NEEDS_INFO


def test_mismatch_beats_decline() -> None:
    output = make_output(recommendation="decline", needs_human=True)
    assert route(make_input(mismatch=0.5), output).status is Status.NEEDS_INFO


def test_high_loan_amount_beats_approve_with_high_confidence() -> None:
    inp = make_input(loan_amount=HIGH_LOAN_AMOUNT_CUTOFF * 2)
    output = make_output(confidence=1.0)
    assert route(inp, output) == RouteResult(Status.PENDING_REVIEW)


def test_decline_beats_high_confidence() -> None:
    output = make_output(recommendation="decline", confidence=1.0, needs_human=True)
    assert route(make_input(), output) == RouteResult(Status.PENDING_REVIEW)


def test_only_needs_info_carries_a_human_question() -> None:
    cases = [
        route(make_input(loan_amount=HIGH_LOAN_AMOUNT_CUTOFF * 2), make_output()),
        route(make_input(), make_output(recommendation="refer", needs_human=True)),
        route(make_input(), make_output(needs_human=True)),
        route(make_input(), make_output(confidence=0.1)),
        route(make_input(), make_output()),
    ]
    assert all(result.human_question is None for result in cases)


# --- invariants over a grid of inputs ---

MISMATCHES = [None, 0.0, INCOME_MISMATCH_TOLERANCE, above(INCOME_MISMATCH_TOLERANCE), 0.5]
LOANS = [SMALL_LOAN, HIGH_LOAN_AMOUNT_CUTOFF, above(HIGH_LOAN_AMOUNT_CUTOFF)]
CONFIDENCES = [0.0, below(MIN_AUTO_CLEAR_CONFIDENCE), MIN_AUTO_CLEAR_CONFIDENCE, 1.0]
GRID = list(itertools.product(MISMATCHES, LOANS, CONFIDENCES))


@pytest.mark.parametrize(("mismatch", "loan_amount", "confidence"), GRID)
def test_decline_never_auto_clears(
    mismatch: float | None, loan_amount: float, confidence: float
) -> None:
    inp = make_input(mismatch=mismatch, loan_amount=loan_amount)
    output = make_output(recommendation="decline", confidence=confidence, needs_human=True)
    assert route(inp, output).status is not Status.AUTO_CLEARED


@pytest.mark.parametrize(("mismatch", "loan_amount", "confidence"), GRID)
def test_needs_human_can_only_escalate(
    mismatch: float | None, loan_amount: float, confidence: float
) -> None:
    # needs_human=False is only valid with approve, so approve is the only recommendation to flip.
    inp = make_input(mismatch=mismatch, loan_amount=loan_amount)
    without = route(inp, make_output(confidence=confidence, needs_human=False))
    with_human = route(inp, make_output(confidence=confidence, needs_human=True))

    assert with_human.status is not Status.AUTO_CLEARED
    if without.status in (Status.PENDING_REVIEW, Status.NEEDS_INFO):
        assert with_human == without
