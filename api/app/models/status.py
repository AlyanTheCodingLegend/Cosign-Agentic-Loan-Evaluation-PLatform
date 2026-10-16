"""Application status enum and allowed transitions, the single source of truth for the flow."""

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType


class Status(StrEnum):
    """Every status an application can be in."""

    SUBMITTED = "submitted"
    ANALYZING = "analyzing"
    NEEDS_INFO = "needs_info"
    PENDING_REVIEW = "pending_review"
    AUTO_CLEARED = "auto_cleared"
    DECIDED = "decided"


ALLOWED_TRANSITIONS: Mapping[Status, frozenset[Status]] = MappingProxyType(
    {
        Status.SUBMITTED: frozenset({Status.ANALYZING}),
        Status.ANALYZING: frozenset(
            {Status.NEEDS_INFO, Status.PENDING_REVIEW, Status.AUTO_CLEARED}
        ),
        Status.NEEDS_INFO: frozenset({Status.ANALYZING}),
        Status.PENDING_REVIEW: frozenset({Status.DECIDED}),
        Status.AUTO_CLEARED: frozenset({Status.DECIDED}),
        Status.DECIDED: frozenset(),
    }
)


class InvalidTransition(Exception):
    """Raised when a status change is not in ALLOWED_TRANSITIONS."""


def transition(current: Status, new: Status) -> Status:
    """Return new if moving from current to new is allowed, else raise InvalidTransition."""
    if new not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransition(f"cannot move from {current} to {new}")
    return new
