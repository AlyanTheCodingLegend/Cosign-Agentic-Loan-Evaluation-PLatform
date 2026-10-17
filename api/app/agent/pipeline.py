"""Orchestrate the agent steps and every status transition for one application."""

import logging
from typing import Any

from app.agent.extraction import extract_fields
from app.agent.metrics import compute_metrics
from app.agent.reasoner import ModelClient, recommend
from app.agent.router import check_completeness, route
from app.db.audit import write_event, write_override
from app.db.store import Store
from app.models.application import (
    ApplicationRecord,
    DecisionAction,
    DecisionRequest,
    FinalDecision,
    ReplyRequest,
)
from app.models.contract import ApplicantFields, ReasonerInput, Recommendation
from app.models.status import InvalidTransition, Status, transition

logger = logging.getLogger(__name__)

PIPELINE_ERROR_EVENT = "pipeline_error"


class InvalidDecision(Exception):
    """Raised when a reviewer decision is not allowed for the application's current state."""


def apply_transition(
    store: Store,
    application_id: str,
    new: Status,
    actor: str = "system",
    **columns: Any,
) -> ApplicationRecord:
    """Check the move with status.transition, update the row and write an audit event."""
    current = store.get_application(application_id).status
    transition(current, new)
    record = store.update_application(application_id, status=new, **columns)
    write_event(
        store,
        application_id,
        "status_changed",
        {"from": current.value, "to": new.value},
        actor=actor,
    )
    return record


def _require(value: float | None, name: str) -> float:
    # check_completeness already ran; this only narrows the type.
    if value is None:
        raise ValueError(f"{name} is missing after the completeness check")
    return value


def _missing_fields_question(missing: list[str]) -> str:
    return "Please provide the following missing information: " + ", ".join(missing) + "."


def run_pipeline(application_id: str, store: Store, model: ModelClient) -> Status:
    """Run extraction, then check_completeness, then metrics, reasoner and router.

    If check_completeness reports missing fields, set needs_info with a human_question naming
    them and skip metrics and the reasoner. Return the resulting status.
    """
    record = apply_transition(application_id=application_id, store=store, new=Status.ANALYZING)
    fields = extract_fields(record.input, model)
    write_event(store, application_id, "fields_extracted", {"fields": fields.model_dump()})

    missing = check_completeness(fields)
    if missing:
        question = _missing_fields_question(missing)
        write_event(store, application_id, "missing_fields", {"missing": missing})
        result = apply_transition(
            store, application_id, Status.NEEDS_INFO, fields=fields, human_question=question
        )
        return result.status

    return _assess(application_id, store, model, fields)


def _assess(
    application_id: str, store: Store, model: ModelClient, fields: ApplicantFields
) -> Status:
    metrics = compute_metrics(
        _require(fields.annual_income, "annual_income"),
        _require(fields.loan_amount, "loan_amount"),
        _require(fields.annuity, "annuity"),
        fields.document_income,
    )
    inp = ReasonerInput(fields=fields, metrics=metrics)
    output = recommend(inp, model)
    write_event(
        store,
        application_id,
        "recommendation",
        {"metrics": metrics.model_dump(), "output": output.model_dump(mode="json")},
    )
    outcome = route(inp, output)
    write_event(
        store,
        application_id,
        "routed",
        {"status": outcome.status.value, "human_question": outcome.human_question},
    )
    return apply_transition(
        store,
        application_id,
        outcome.status,
        fields=fields,
        metrics=metrics,
        agent_output=output,
        human_question=outcome.human_question,
    ).status


def run_pipeline_safely(application_id: str, store: Store, model: ModelClient) -> None:
    """Run the pipeline as a background task; an unexpected crash sends the case to a human."""
    try:
        run_pipeline(application_id, store, model)
    except Exception:
        logger.exception("pipeline failed", extra={"application_id": application_id})
        write_event(store, application_id, PIPELINE_ERROR_EVENT)
        if store.get_application(application_id).status is Status.ANALYZING:
            apply_transition(store, application_id, Status.PENDING_REVIEW)


def apply_reply(application_id: str, reply: ReplyRequest, store: Store) -> ApplicationRecord:
    """Record the applicant's answer so the next pipeline run can use it."""
    record = store.get_application(application_id)
    if record.status is not Status.NEEDS_INFO:
        raise InvalidTransition(f"application is {record.status}, not waiting for a reply")
    corrections = reply.corrections.model_dump(exclude_unset=True, exclude_none=True)
    updated_input = record.input.model_copy(
        update={
            "replies": [*record.input.replies, reply.answer],
            "corrections": {**record.input.corrections, **corrections},
        }
    )
    write_event(
        store,
        application_id,
        "applicant_replied",
        {"corrected_fields": sorted(corrections)},
        actor="applicant",
    )
    return store.update_application(application_id, input=updated_input)


def _agent_recommendation(record: ApplicationRecord) -> Recommendation:
    # No output means the pipeline crashed and the case was sent to a human as a refer.
    return record.agent_output.recommendation if record.agent_output else Recommendation.REFER


def _resolve_final_decision(
    record: ApplicationRecord, request: DecisionRequest
) -> tuple[FinalDecision, bool]:
    """Return the final decision and whether it contradicts the agent (a logged override)."""
    recommendation = _agent_recommendation(record)
    if request.action is DecisionAction.OVERRIDE:
        assert request.final_decision is not None
        return request.final_decision, True
    decision = (
        FinalDecision.APPROVE if request.action is DecisionAction.APPROVE else FinalDecision.REJECT
    )
    contradicts = (
        decision is FinalDecision.APPROVE and recommendation is Recommendation.DECLINE
    ) or (decision is FinalDecision.REJECT and recommendation is Recommendation.APPROVE)
    if contradicts:
        raise InvalidDecision(
            f"{request.action} contradicts the agent's {recommendation}; use override with a reason"
        )
    return decision, False


def apply_decision(
    application_id: str, request: DecisionRequest, store: Store
) -> ApplicationRecord:
    """Record a reviewer's decision, log any override with its reason, and mark decided."""
    record = store.get_application(application_id)
    if record.status not in (Status.PENDING_REVIEW, Status.AUTO_CLEARED):
        raise InvalidTransition(f"cannot decide an application that is {record.status}")
    decision, is_override = _resolve_final_decision(record, request)
    if is_override:
        write_override(
            store,
            application_id,
            request.reviewer_id,
            _agent_recommendation(record),
            decision,
            request.reason or "",
        )
    write_event(
        store,
        application_id,
        "reviewer_decision",
        {
            "action": request.action.value,
            "final_decision": decision.value,
            "reason": request.reason,
        },
        actor=request.reviewer_id,
    )
    return apply_transition(
        store,
        application_id,
        Status.DECIDED,
        actor=request.reviewer_id,
        final_decision=decision,
        decision_reason=request.reason,
        decided_by=request.reviewer_id,
    )
