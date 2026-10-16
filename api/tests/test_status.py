import itertools

import pytest

from app.models.status import ALLOWED_TRANSITIONS, InvalidTransition, Status, transition

# Written out by hand from the CLAUDE.md pipeline, not derived from ALLOWED_TRANSITIONS.
LEGAL = {
    (Status.SUBMITTED, Status.ANALYZING),
    (Status.ANALYZING, Status.NEEDS_INFO),
    (Status.ANALYZING, Status.PENDING_REVIEW),
    (Status.ANALYZING, Status.AUTO_CLEARED),
    (Status.NEEDS_INFO, Status.ANALYZING),
    (Status.PENDING_REVIEW, Status.DECIDED),
    (Status.AUTO_CLEARED, Status.DECIDED),
}
ILLEGAL = sorted(set(itertools.product(Status, Status)) - LEGAL)


@pytest.mark.parametrize(("current", "new"), sorted(LEGAL))
def test_legal_transition_returns_new_status(current: Status, new: Status) -> None:
    assert transition(current, new) is new


@pytest.mark.parametrize(("current", "new"), ILLEGAL)
def test_illegal_transition_raises(current: Status, new: Status) -> None:
    with pytest.raises(InvalidTransition):
        transition(current, new)


def test_every_pair_is_covered() -> None:
    assert len(LEGAL) + len(ILLEGAL) == len(Status) ** 2


def test_every_status_has_an_entry() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(Status)


def test_decided_is_terminal() -> None:
    assert ALLOWED_TRANSITIONS[Status.DECIDED] == frozenset()


def test_needs_info_goes_back_to_analyzing() -> None:
    assert ALLOWED_TRANSITIONS[Status.NEEDS_INFO] == frozenset({Status.ANALYZING})
