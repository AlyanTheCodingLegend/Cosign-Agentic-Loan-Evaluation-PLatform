"""Thin HTTP handlers for applications: parse, call the pipeline, return."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from app.agent.pipeline import (
    InvalidDecision,
    apply_decision,
    apply_reply,
    run_pipeline_safely,
)
from app.agent.reasoner import ModelClient, get_model_client
from app.db.audit import write_event
from app.db.store import ApplicationNotFound, Store, get_store
from app.models.application import (
    ApplicationInput,
    DecisionRequest,
    FinalDecision,
    ReplyRequest,
)
from app.models.status import InvalidTransition, Status

router = APIRouter(prefix="/applications", tags=["applications"])

StoreDep = Annotated[Store, Depends(get_store)]
ModelDep = Annotated[ModelClient, Depends(get_model_client)]


class ApplicationAccepted(BaseModel):
    """Returned when work has started; follow progress through Supabase realtime."""

    id: str
    status: Status


class DecisionResult(BaseModel):
    """Returned after a reviewer decision."""

    id: str
    status: Status
    final_decision: FinalDecision | None


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_application(
    body: ApplicationInput,
    background: BackgroundTasks,
    store: StoreDep,
    model: ModelDep,
) -> ApplicationAccepted:
    """Create an application and start the pipeline in the background."""
    record = store.create_application(body)
    write_event(store, record.id, "application_submitted", actor="applicant")
    background.add_task(run_pipeline_safely, record.id, store, model)
    return ApplicationAccepted(id=record.id, status=record.status)


@router.post("/{application_id}/reply", status_code=status.HTTP_202_ACCEPTED)
def reply_to_question(
    application_id: str,
    body: ReplyRequest,
    background: BackgroundTasks,
    store: StoreDep,
    model: ModelDep,
) -> ApplicationAccepted:
    """Carry the applicant's answer to a human_question and re-run the pipeline."""
    try:
        record = apply_reply(application_id, body, store)
    except ApplicationNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "application not found") from exc
    except InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    background.add_task(run_pipeline_safely, application_id, store, model)
    return ApplicationAccepted(id=record.id, status=record.status)


@router.post("/{application_id}/decision")
def decide(application_id: str, body: DecisionRequest, store: StoreDep) -> DecisionResult:
    """Carry a reviewer's approve, reject or override. Reject and override need a reason."""
    try:
        record = apply_decision(application_id, body, store)
    except ApplicationNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "application not found") from exc
    except (InvalidTransition, InvalidDecision) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return DecisionResult(id=record.id, status=record.status, final_decision=record.final_decision)
