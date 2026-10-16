"""Append-only writers for the audit log and the override log."""

from datetime import UTC, datetime

from app.db.store import Store
from app.models.application import AuditEvent, FinalDecision, OverrideEntry
from app.models.contract import Recommendation

SYSTEM_ACTOR = "system"


def write_event(
    store: Store,
    application_id: str,
    event_type: str,
    payload: dict[str, object] | None = None,
    actor: str = SYSTEM_ACTOR,
) -> None:
    """Append one event to the audit log. Never updates or deletes."""
    store.append_event(
        AuditEvent(
            application_id=application_id,
            actor=actor,
            event_type=event_type,
            payload=payload or {},
            created_at=datetime.now(UTC),
        )
    )


def write_override(
    store: Store,
    application_id: str,
    reviewer_id: str,
    original: Recommendation,
    decision: FinalDecision,
    reason: str,
) -> None:
    """Append one reviewer override with its required reason to the override log."""
    store.append_override(
        OverrideEntry(
            application_id=application_id,
            reviewer_id=reviewer_id,
            agent_recommendation=original.value,
            human_decision=decision,
            reason=reason,
            created_at=datetime.now(UTC),
        )
    )
