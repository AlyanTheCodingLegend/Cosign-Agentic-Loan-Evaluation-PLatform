"""Append-only writers for the audit log and the override log."""

from app.models.contract import Recommendation


def write_event(application_id: str, event_type: str, payload: dict[str, object]) -> None:
    """Append one event to the audit log. Never updates or deletes."""
    raise NotImplementedError


def write_override(
    application_id: str,
    reviewer_id: str,
    original: Recommendation,
    decision: Recommendation,
    reason: str,
) -> None:
    """Append one reviewer override with its required reason to the override log."""
    raise NotImplementedError
