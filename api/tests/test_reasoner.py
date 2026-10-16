import json
from typing import Any

import pytest

from app.agent.fake_model import FakeModelClient
from app.agent.metrics import compute_metrics
from app.agent.reasoner import (
    FALLBACK_REASON,
    ModelError,
    build_prompt,
    recommend,
)
from app.models.contract import ApplicantFields, ReasonerInput, Recommendation

VALID_APPROVE = json.dumps(
    {
        "recommendation": "approve",
        "confidence": 0.9,
        "reasons": ["payment_to_income 0.15 is low"],
        "needs_human": False,
        "human_question": None,
    }
)


class ScriptedClient:
    """Returns or raises the scripted items in order, then repeats the last one."""

    def __init__(self, *script: str | Exception) -> None:
        self._script = list(script)
        self.calls = 0

    def complete_json(
        self, system: str, user: str, schema_name: str, schema: dict[str, Any]
    ) -> str:
        item = self._script[min(self.calls, len(self._script) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item


def _input(complete_fields: dict[str, object]) -> ReasonerInput:
    fields = ApplicantFields.model_validate(complete_fields)
    assert fields.annual_income and fields.loan_amount and fields.annuity
    metrics = compute_metrics(
        fields.annual_income, fields.loan_amount, fields.annuity, fields.document_income
    )
    return ReasonerInput(fields=fields, metrics=metrics)


def test_valid_output_is_returned_on_first_try(complete_fields: dict[str, object]) -> None:
    client = ScriptedClient(VALID_APPROVE)

    output = recommend(_input(complete_fields), client)

    assert output.recommendation is Recommendation.APPROVE
    assert client.calls == 1


def test_invalid_json_is_retried_once(complete_fields: dict[str, object]) -> None:
    client = ScriptedClient("not json", VALID_APPROVE)

    output = recommend(_input(complete_fields), client)

    assert output.recommendation is Recommendation.APPROVE
    assert client.calls == 2


def test_contract_violation_counts_as_invalid(complete_fields: dict[str, object]) -> None:
    bad = json.dumps(
        {
            "recommendation": "decline",
            "confidence": 0.9,
            "reasons": ["x"],
            "needs_human": False,
            "human_question": None,
        }
    )
    client = ScriptedClient(bad, VALID_APPROVE)

    output = recommend(_input(complete_fields), client)

    assert output.recommendation is Recommendation.APPROVE
    assert client.calls == 2


@pytest.mark.parametrize("failure", ["not json", ModelError("timeout")])
def test_two_failures_fall_back_to_refer(
    complete_fields: dict[str, object], failure: str | Exception
) -> None:
    client = ScriptedClient(failure)

    output = recommend(_input(complete_fields), client)

    assert client.calls == 2
    assert output.recommendation is Recommendation.REFER
    assert output.needs_human is True
    assert output.reasons == [FALLBACK_REASON]


def test_prompt_contains_metrics_and_no_protected_terms(
    complete_fields: dict[str, object],
) -> None:
    prompt = build_prompt(_input(complete_fields)).lower()

    assert "payment_to_income" in prompt
    assert "loan_to_income" in prompt
    for term in ("gender", "birth", "age", "family", "marital"):
        assert term not in prompt


def test_fake_model_approves_a_healthy_case(complete_fields: dict[str, object]) -> None:
    inp = _input({**complete_fields, "annuity": 3_000.0, "ext_source_1": 0.7, "ext_source_3": 0.7})

    output = recommend(inp, FakeModelClient())

    assert output.recommendation is Recommendation.APPROVE
    assert output.confidence == 0.9


def test_fake_model_declines_unaffordable_payment(complete_fields: dict[str, object]) -> None:
    inp = _input({**complete_fields, "annuity": 6_500.0, "ext_source_1": 0.7})

    output = recommend(inp, FakeModelClient())

    assert output.recommendation is Recommendation.DECLINE
    assert output.needs_human is True


def test_fake_model_refers_when_all_scores_missing(complete_fields: dict[str, object]) -> None:
    inp = _input({**complete_fields, "ext_source_2": None})

    output = recommend(inp, FakeModelClient())

    assert output.recommendation is Recommendation.REFER
    assert output.human_question is not None
