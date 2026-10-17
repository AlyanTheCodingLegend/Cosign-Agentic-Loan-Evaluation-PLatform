import asyncio

import pytest

from app.agent.pipeline import apply_transition
from app.db.store import InMemoryStore
from app.mcp.server import (
    build_server,
    compute_metrics,
    flag_for_review,
    get_application,
    log_event,
    request_info,
)
from app.models.application import ApplicationForm, ApplicationInput
from app.models.status import InvalidTransition, Status


def _analyzing(store: InMemoryStore, **form: float) -> str:
    base = {"annual_income": 120_000.0, "loan_amount": 240_000.0, "annuity": 2_500.0}
    record = store.create_application(
        ApplicationInput(form=ApplicationForm(**{**base, **form}, goods_price=220_000.0))
    )
    apply_transition(store, record.id, Status.ANALYZING)
    return record.id


def test_get_application_returns_record() -> None:
    store = InMemoryStore()
    application_id = _analyzing(store)

    assert get_application(store, application_id).id == application_id


def test_compute_metrics_uses_code_arithmetic() -> None:
    store = InMemoryStore()
    application_id = _analyzing(store)

    metrics = compute_metrics(store, application_id)

    assert metrics.loan_to_income == 2.0
    assert metrics.payment_to_income == 0.25


def test_compute_metrics_rejects_incomplete_application() -> None:
    store = InMemoryStore()
    record = store.create_application(ApplicationInput(form=ApplicationForm(annual_income=1.0)))

    with pytest.raises(ValueError, match="missing fields"):
        compute_metrics(store, record.id)


def test_request_info_sets_question_and_status() -> None:
    store = InMemoryStore()
    application_id = _analyzing(store)

    request_info(store, application_id, "Which income is right?")

    record = store.get_application(application_id)
    assert record.status is Status.NEEDS_INFO
    assert record.human_question == "Which income is right?"


def test_flag_for_review_logs_reason_and_moves_status() -> None:
    store = InMemoryStore()
    application_id = _analyzing(store)

    flag_for_review(store, application_id, "Unusual employment history")

    assert store.get_application(application_id).status is Status.PENDING_REVIEW
    events = {e.event_type: e for e in store.list_events(application_id)}
    assert events["flagged_for_review"].payload == {"reason": "Unusual employment history"}
    assert events["flagged_for_review"].actor == "agent"


def test_flag_for_review_from_wrong_state_is_rejected() -> None:
    store = InMemoryStore()
    record = store.create_application(ApplicationInput(form=ApplicationForm()))

    with pytest.raises(InvalidTransition):
        flag_for_review(store, record.id, "reason")


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_question_and_reason_are_rejected(blank: str) -> None:
    store = InMemoryStore()
    application_id = _analyzing(store)

    with pytest.raises(ValueError):
        request_info(store, application_id, blank)
    with pytest.raises(ValueError):
        flag_for_review(store, application_id, blank)


def test_log_event_appends_to_audit_log() -> None:
    store = InMemoryStore()
    application_id = _analyzing(store)

    log_event(store, application_id, "note", {"a": 1})

    assert store.list_events(application_id)[-1].event_type == "note"


def test_server_registers_all_five_tools() -> None:
    server = build_server(InMemoryStore())

    names = {tool.name for tool in asyncio.run(server.list_tools())}

    assert names == {
        "get_application",
        "compute_metrics",
        "request_info",
        "flag_for_review",
        "log_event",
    }
