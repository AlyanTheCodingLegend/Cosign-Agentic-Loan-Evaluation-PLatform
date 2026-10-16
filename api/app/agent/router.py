"""Routing rules as pure functions. The model recommends; these rules decide the path."""

from app.models.contract import REQUIRED_FIELDS, ApplicantFields, ReasonerInput, ReasonerOutput
from app.models.status import Status


def check_completeness(fields: ApplicantFields) -> list[str]:
    """Return the names of missing required fields in REQUIRED_FIELDS order; empty if complete."""
    return [name for name in REQUIRED_FIELDS if getattr(fields, name) is None]


def route(inp: ReasonerInput, output: ReasonerOutput) -> Status:
    """Return needs_info, pending_review or auto_cleared by the ordered rules in CLAUDE.md.

    Missing required fields never reach here: check_completeness runs right after extraction.
    """
    raise NotImplementedError
