"""Application input as submitted, request bodies, and the stored application record."""

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.contract import ApplicantFields, Metrics, ReasonerOutput
from app.models.status import Status


class DocumentKind(StrEnum):
    """Supporting document types the applicant can attach."""

    SALARY_SLIP = "salary_slip"
    BANK_STATEMENT = "bank_statement"
    OTHER = "other"


class Document(BaseModel):
    """One supporting document, already converted to text."""

    name: str = Field(min_length=1)
    kind: DocumentKind = DocumentKind.OTHER
    text: str


class ApplicationForm(BaseModel):
    """What the applicant typed into the form. Every number may be left out.

    Unknown keys (for example gender or birth date from a raw data row) are ignored, so
    protected attributes are dropped at the boundary and never stored (hard rule 4).
    """

    model_config = ConfigDict(extra="ignore")

    annual_income: float | None = None
    loan_amount: float | None = None
    annuity: float | None = None
    goods_price: float | None = None
    years_employed: float | None = None
    ext_source_1: float | None = None
    ext_source_2: float | None = None
    ext_source_3: float | None = None


class ApplicationInput(BaseModel):
    """The submitted form and documents for one application, plus later applicant replies."""

    form: ApplicationForm
    documents: list[Document] = Field(default_factory=list)
    replies: list[str] = Field(default_factory=list)
    # Field values the applicant corrected in a reply. They win over extracted values.
    corrections: dict[str, float] = Field(default_factory=dict)


class ReplyRequest(BaseModel):
    """The applicant's answer to a human_question, with optional corrected field values."""

    answer: str = Field(min_length=1)
    corrections: ApplicantFields = Field(default_factory=ApplicantFields)

    @model_validator(mode="after")
    def _answer_not_blank(self) -> Self:
        if not self.answer.strip():
            raise ValueError("answer must not be blank")
        return self


class DecisionAction(StrEnum):
    """What the reviewer does with a case."""

    APPROVE = "approve"
    REJECT = "reject"
    OVERRIDE = "override"


class FinalDecision(StrEnum):
    """The outcome recorded on a decided application."""

    APPROVE = "approve"
    REJECT = "reject"


class DecisionRequest(BaseModel):
    """A reviewer's decision. Reject and override require a reason (hard rule 6)."""

    reviewer_id: str = Field(min_length=1)
    action: DecisionAction
    # Only for override: the outcome the reviewer chooses against the agent's recommendation.
    final_decision: FinalDecision | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def _check_action_fields(self) -> Self:
        needs_reason = self.action in (DecisionAction.REJECT, DecisionAction.OVERRIDE)
        if needs_reason and not (self.reason and self.reason.strip()):
            raise ValueError(f"a reason is required for {self.action}")
        if self.action is DecisionAction.OVERRIDE and self.final_decision is None:
            raise ValueError("final_decision is required for override")
        if self.action is not DecisionAction.OVERRIDE and self.final_decision is not None:
            raise ValueError("final_decision is only allowed for override")
        return self


class ApplicationRecord(BaseModel):
    """One row of the applications table."""

    id: str
    status: Status
    input: ApplicationInput
    fields: ApplicantFields | None = None
    metrics: Metrics | None = None
    agent_output: ReasonerOutput | None = None
    human_question: str | None = None
    final_decision: FinalDecision | None = None
    decision_reason: str | None = None
    decided_by: str | None = None
    created_at: datetime
    updated_at: datetime


class AuditEvent(BaseModel):
    """One row of the append-only audit log."""

    application_id: str
    actor: str
    event_type: str
    payload: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class OverrideEntry(BaseModel):
    """One row of the append-only override log."""

    application_id: str
    reviewer_id: str
    agent_recommendation: str
    human_decision: FinalDecision
    reason: str = Field(min_length=1)
    created_at: datetime
