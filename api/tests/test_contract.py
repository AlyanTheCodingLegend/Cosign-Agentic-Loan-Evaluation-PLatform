import pytest
from pydantic import ValidationError

from app.models.contract import (
    REQUIRED_FIELDS,
    ApplicantFields,
    Metrics,
    ReasonerInput,
    ReasonerOutput,
)


def output(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "recommendation": "approve",
        "confidence": 0.9,
        "reasons": ["payment_to_income 0.18 is below the limit"],
        "needs_human": False,
        "human_question": None,
    }
    data.update(overrides)
    return data


METRICS = Metrics(loan_to_income=2.5, payment_to_income=0.18, income_mismatch_pct=0.02)


# --- ReasonerOutput ---


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({}, id="approve-no-human"),
        pytest.param(
            {"needs_human": True, "human_question": "Confirm employer?"}, id="approve-with-human"
        ),
        pytest.param({"recommendation": "decline", "needs_human": True}, id="decline-no-question"),
        pytest.param(
            {"recommendation": "refer", "needs_human": True, "human_question": "Upload payslip?"},
            id="refer-with-question",
        ),
        pytest.param(
            {
                "recommendation": "refer",
                "confidence": 0.0,
                "reasons": ["model output invalid after retry"],
                "needs_human": True,
            },
            id="rule-7-fallback",
        ),
        pytest.param({"confidence": 0.0}, id="confidence-0"),
        pytest.param({"confidence": 1.0}, id="confidence-1"),
    ],
)
def test_reasoner_output_valid(overrides: dict[str, object]) -> None:
    ReasonerOutput.model_validate(output(**overrides))


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"recommendation": "decline"}, id="decline-without-human"),
        pytest.param({"recommendation": "refer"}, id="refer-without-human"),
        pytest.param({"human_question": "Why?"}, id="question-without-human"),
        pytest.param({"reasons": []}, id="no-reasons"),
        pytest.param({"confidence": -0.01}, id="confidence-below-0"),
        pytest.param({"confidence": 1.01}, id="confidence-above-1"),
        pytest.param({"recommendation": "maybe"}, id="unknown-recommendation"),
    ],
)
def test_reasoner_output_invalid(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ReasonerOutput.model_validate(output(**overrides))


def test_reasoner_output_missing_field_is_invalid() -> None:
    data = output()
    del data["human_question"]
    with pytest.raises(ValidationError):
        ReasonerOutput.model_validate(data)


def test_reasoner_output_parses_raw_json() -> None:
    raw = (
        '{"recommendation": "refer", "confidence": 0.55, '
        '"reasons": ["ext_source_1 is missing"], "needs_human": true, '
        '"human_question": "Provide a credit bureau report?"}'
    )
    parsed = ReasonerOutput.model_validate_json(raw)
    assert parsed.recommendation == "refer"
    assert parsed.needs_human is True


def test_reasoner_output_rejects_invalid_json() -> None:
    with pytest.raises(ValidationError):
        ReasonerOutput.model_validate_json('{"recommendation": "approve"')


# --- ApplicantFields ---


def test_applicant_fields_allow_missing_values() -> None:
    fields = ApplicantFields(stated_income_source="form")
    assert fields.annual_income is None


def test_applicant_fields_reject_protected_attribute(complete_fields: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ApplicantFields.model_validate({**complete_fields, "gender": "F"})


def test_applicant_fields_reject_unknown_income_source(
    complete_fields: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ApplicantFields.model_validate({**complete_fields, "stated_income_source": "guess"})


# --- ReasonerInput ---


def test_reasoner_input_accepts_complete_fields(complete_fields: dict[str, object]) -> None:
    fields = ApplicantFields.model_validate(complete_fields)
    ReasonerInput(fields=fields, metrics=METRICS)


@pytest.mark.parametrize("missing", REQUIRED_FIELDS)
def test_reasoner_input_rejects_incomplete_fields(
    complete_fields: dict[str, object], missing: str
) -> None:
    fields = ApplicantFields.model_validate({**complete_fields, missing: None})
    with pytest.raises(ValidationError, match=missing):
        ReasonerInput(fields=fields, metrics=METRICS)
