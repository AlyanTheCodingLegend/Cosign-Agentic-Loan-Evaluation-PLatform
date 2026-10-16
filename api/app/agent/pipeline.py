"""Orchestrate the agent steps and every status transition for one application."""

from app.models.status import Status


def run_pipeline(application_id: str) -> Status:
    """Run extraction, then check_completeness, then metrics, reasoner and router.

    If check_completeness reports missing fields, set needs_info with a human_question naming
    them and skip metrics and the reasoner. Return the resulting status.
    """
    raise NotImplementedError


def apply_transition(application_id: str, new: Status) -> None:
    """Check the move with status.transition, update the row and write an audit event."""
    raise NotImplementedError
