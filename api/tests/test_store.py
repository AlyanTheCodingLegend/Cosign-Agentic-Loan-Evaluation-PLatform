import pytest

from app.db.audit import write_event, write_override
from app.db.store import ApplicationNotFound, InMemoryStore
from app.models.application import ApplicationForm, ApplicationInput, FinalDecision
from app.models.contract import Recommendation
from app.models.status import Status


def _input() -> ApplicationInput:
    return ApplicationInput(form=ApplicationForm(annual_income=100_000.0))


def test_create_starts_submitted() -> None:
    record = InMemoryStore().create_application(_input())

    assert record.status is Status.SUBMITTED
    assert record.input.form.annual_income == 100_000.0


def test_update_changes_columns_and_bumps_updated_at() -> None:
    store = InMemoryStore()
    record = store.create_application(_input())

    updated = store.update_application(record.id, status=Status.ANALYZING)

    assert updated.status is Status.ANALYZING
    assert updated.updated_at >= record.updated_at
    assert store.get_application(record.id).status is Status.ANALYZING


def test_get_returns_copy() -> None:
    store = InMemoryStore()
    record = store.create_application(_input())
    record.input.form.annual_income = 1.0

    assert store.get_application(record.id).input.form.annual_income == 100_000.0


def test_unknown_id_raises() -> None:
    with pytest.raises(ApplicationNotFound):
        InMemoryStore().get_application("missing")


def test_events_are_scoped_to_application() -> None:
    store = InMemoryStore()
    a = store.create_application(_input())
    b = store.create_application(_input())

    write_event(store, a.id, "created", {"x": 1})
    write_event(store, b.id, "created")

    events = store.list_events(a.id)
    assert [e.event_type for e in events] == ["created"]
    assert events[0].actor == "system"
    assert events[0].payload == {"x": 1}


def test_event_for_unknown_application_is_rejected() -> None:
    with pytest.raises(ApplicationNotFound):
        write_event(InMemoryStore(), "missing", "created")


def test_override_is_stored_with_reason() -> None:
    store = InMemoryStore()
    record = store.create_application(_input())

    write_override(
        store, record.id, "rev-1", Recommendation.DECLINE, FinalDecision.APPROVE, "Verified income"
    )

    [entry] = store.list_overrides()
    assert entry.agent_recommendation == "decline"
    assert entry.human_decision is FinalDecision.APPROVE
    assert entry.reason == "Verified income"
