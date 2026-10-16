import json
from pathlib import Path
from typing import Any

import pytest

from app.agent.fake_model import FakeModelClient
from app.agent.pipeline import (
    InvalidDecision,
    apply_decision,
    apply_reply,
    run_pipeline,
    run_pipeline_safely,
)
from app.db.store import InMemoryStore
from app.models.application import (
    ApplicationInput,
    DecisionAction,
    DecisionRequest,
    FinalDecision,
    ReplyRequest,
)
from app.models.contract import Recommendation
from app.models.status import InvalidTransition, Status

SEED_PATH = Path(__file__).resolve().parents[1] / "seed" / "demo_applicants.json"
DEMO: list[dict[str, Any]] = json.loads(SEED_PATH.read_text(encoding="utf-8"))
MODEL = FakeModelClient()


def _submit(store: InMemoryStore, entry: dict[str, Any]) -> str:
    return store.create_application(ApplicationInput.model_validate(entry["input"])).id


def _event_types(store: InMemoryStore, application_id: str) -> list[str]:
    return [e.event_type for e in store.list_events(application_id)]


@pytest.mark.parametrize("entry", DEMO, ids=[e["key"] for e in DEMO])
def test_demo_applicant_reaches_expected_status(entry: dict[str, Any]) -> None:
    store = InMemoryStore()
    application_id = _submit(store, entry)

    status = run_pipeline(application_id, store, MODEL)

    assert status.value == entry["expected_status"]
    record = store.get_application(application_id)
    assert record.status is status
    events = _event_types(store, application_id)
    for expected in entry["expected_events"]:
        assert expected in events
    assert events.count("status_changed") == 2


@pytest.mark.parametrize(
    "entry", [e for e in DEMO if "reply" in e], ids=[e["key"] for e in DEMO if "reply" in e]
)
def test_reply_resumes_the_pipeline(entry: dict[str, Any]) -> None:
    store = InMemoryStore()
    application_id = _submit(store, entry)
    run_pipeline(application_id, store, MODEL)
    assert store.get_application(application_id).human_question

    apply_reply(application_id, ReplyRequest.model_validate(entry["reply"]), store)
    status = run_pipeline(application_id, store, MODEL)

    assert status.value == entry["reply"]["expected_status"]
    assert store.get_application(application_id).human_question is None
    assert "applicant_replied" in _event_types(store, application_id)


def test_missing_field_question_names_the_field() -> None:
    store = InMemoryStore()
    entry = next(e for e in DEMO if e["key"] == "missing_annuity")

    application_id = _submit(store, entry)
    run_pipeline(application_id, store, MODEL)

    record = store.get_application(application_id)
    assert record.human_question is not None
    assert "annuity" in record.human_question
    assert record.agent_output is None
    assert record.metrics is None


def test_income_mismatch_question_names_both_figures() -> None:
    store = InMemoryStore()
    entry = next(e for e in DEMO if e["key"] == "income_mismatch")

    application_id = _submit(store, entry)
    run_pipeline(application_id, store, MODEL)

    question = store.get_application(application_id).human_question
    assert question is not None
    assert "120,000.00" in question
    assert "80,000.00" in question


def test_reply_outside_needs_info_is_rejected() -> None:
    store = InMemoryStore()
    application_id = _submit(store, DEMO[0])

    with pytest.raises(InvalidTransition):
        apply_reply(application_id, ReplyRequest(answer="hi"), store)


def test_decline_is_never_auto_cleared() -> None:
    store = InMemoryStore()
    entry = next(e for e in DEMO if e["key"] == "unaffordable_decline")

    application_id = _submit(store, entry)
    run_pipeline(application_id, store, MODEL)

    record = store.get_application(application_id)
    assert record.agent_output is not None
    assert record.agent_output.recommendation is Recommendation.DECLINE
    assert record.status is Status.PENDING_REVIEW


def _pending(store: InMemoryStore, key: str) -> str:
    entry = next(e for e in DEMO if e["key"] == key)
    application_id = _submit(store, entry)
    run_pipeline(application_id, store, MODEL)
    return application_id


def test_reviewer_rejects_a_decline_with_reason() -> None:
    store = InMemoryStore()
    application_id = _pending(store, "unaffordable_decline")

    record = apply_decision(
        application_id,
        DecisionRequest(reviewer_id="r1", action=DecisionAction.REJECT, reason="Payment too high"),
        store,
    )

    assert record.status is Status.DECIDED
    assert record.final_decision is FinalDecision.REJECT
    assert record.decided_by == "r1"
    assert store.list_overrides() == []
    assert "reviewer_decision" in _event_types(store, application_id)


def test_override_is_logged_with_reason_and_reviewer() -> None:
    store = InMemoryStore()
    application_id = _pending(store, "unaffordable_decline")

    record = apply_decision(
        application_id,
        DecisionRequest(
            reviewer_id="r1",
            action=DecisionAction.OVERRIDE,
            final_decision=FinalDecision.APPROVE,
            reason="Applicant has a co-signer",
        ),
        store,
    )

    assert record.final_decision is FinalDecision.APPROVE
    [entry] = store.list_overrides()
    assert entry.agent_recommendation == "decline"
    assert entry.human_decision is FinalDecision.APPROVE
    assert entry.reason == "Applicant has a co-signer"
    assert entry.reviewer_id == "r1"


def test_plain_approve_of_a_decline_must_use_override() -> None:
    store = InMemoryStore()
    application_id = _pending(store, "unaffordable_decline")

    with pytest.raises(InvalidDecision):
        apply_decision(
            application_id, DecisionRequest(reviewer_id="r1", action=DecisionAction.APPROVE), store
        )

    assert store.get_application(application_id).status is Status.PENDING_REVIEW


def test_decided_is_terminal() -> None:
    store = InMemoryStore()
    application_id = _pending(store, "borderline_refer")
    request = DecisionRequest(reviewer_id="r1", action=DecisionAction.APPROVE)
    apply_decision(application_id, request, store)

    with pytest.raises(InvalidTransition):
        apply_decision(application_id, request, store)


def test_auto_cleared_can_be_decided() -> None:
    store = InMemoryStore()
    application_id = _pending(store, "clean_approve")

    record = apply_decision(
        application_id, DecisionRequest(reviewer_id="r1", action=DecisionAction.APPROVE), store
    )

    assert record.status is Status.DECIDED


def test_pipeline_crash_sends_case_to_a_human() -> None:
    class Boom:
        def complete_json(
            self, system: str, user: str, schema_name: str, schema: dict[str, Any]
        ) -> str:
            raise RuntimeError("unexpected")

    store = InMemoryStore()
    application_id = _submit(store, DEMO[0])

    run_pipeline_safely(application_id, store, Boom())

    assert store.get_application(application_id).status is Status.PENDING_REVIEW
    assert "pipeline_error" in _event_types(store, application_id)


def test_every_status_change_is_audited() -> None:
    store = InMemoryStore()
    application_id = _pending(store, "borderline_refer")
    apply_decision(
        application_id, DecisionRequest(reviewer_id="r1", action=DecisionAction.APPROVE), store
    )

    changes = [
        (e.payload["from"], e.payload["to"])
        for e in store.list_events(application_id)
        if e.event_type == "status_changed"
    ]

    assert changes == [
        ("submitted", "analyzing"),
        ("analyzing", "pending_review"),
        ("pending_review", "decided"),
    ]
