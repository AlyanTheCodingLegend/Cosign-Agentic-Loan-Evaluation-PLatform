"""MCP server and tool definitions."""

from mcp.server.mcpserver import MCPServer

from app.agent.extraction import merge_fields
from app.agent.metrics import compute_metrics as compute_metrics_from_fields
from app.agent.pipeline import apply_transition
from app.agent.router import check_completeness
from app.db.audit import write_event
from app.db.store import Store, get_store
from app.models.application import ApplicationRecord
from app.models.contract import Metrics
from app.models.status import Status

AGENT_ACTOR = "agent"


def get_application(store: Store, application_id: str) -> ApplicationRecord:
    """Return the application with the given id."""
    return store.get_application(application_id)


def compute_metrics(store: Store, application_id: str) -> Metrics:
    """Compute metrics for the application with the given id, in code."""
    record = store.get_application(application_id)
    fields = record.fields or merge_fields(record.input, None)
    missing = check_completeness(fields)
    if missing:
        raise ValueError(f"cannot compute metrics, missing fields: {', '.join(missing)}")
    return compute_metrics_from_fields(
        _positive(fields.annual_income),
        _positive(fields.loan_amount),
        _positive(fields.annuity),
        fields.document_income,
    )


def _positive(value: float | None) -> float:
    # Completeness was checked; this only narrows the type.
    if value is None:
        raise ValueError("required field is missing")
    return value


def request_info(store: Store, application_id: str, question: str) -> None:
    """Ask the applicant a specific question and move the application to needs_info."""
    if not question.strip():
        raise ValueError("question must not be blank")
    apply_transition(
        store, application_id, Status.NEEDS_INFO, actor=AGENT_ACTOR, human_question=question
    )


def flag_for_review(store: Store, application_id: str, reason: str) -> None:
    """Send the application to the reviewer queue with a reason."""
    if not reason.strip():
        raise ValueError("reason must not be blank")
    write_event(store, application_id, "flagged_for_review", {"reason": reason}, actor=AGENT_ACTOR)
    apply_transition(store, application_id, Status.PENDING_REVIEW, actor=AGENT_ACTOR)


def log_event(
    store: Store, application_id: str, event_type: str, payload: dict[str, object]
) -> None:
    """Append an event to the audit log."""
    write_event(store, application_id, event_type, payload, actor=AGENT_ACTOR)


def build_server(store: Store | None = None) -> MCPServer:
    """Create the MCP server and register every tool."""
    backing = store or get_store()
    server = MCPServer("loan-approval-agent")

    @server.tool(name="get_application")
    def _get_application(application_id: str) -> ApplicationRecord:
        """Return the application with the given id."""
        return get_application(backing, application_id)

    @server.tool(name="compute_metrics")
    def _compute_metrics(application_id: str) -> Metrics:
        """Compute loan-to-income, payment-to-income and income mismatch in code."""
        return compute_metrics(backing, application_id)

    @server.tool(name="request_info")
    def _request_info(application_id: str, question: str) -> None:
        """Ask the applicant a specific question and move the application to needs_info."""
        request_info(backing, application_id, question)

    @server.tool(name="flag_for_review")
    def _flag_for_review(application_id: str, reason: str) -> None:
        """Send the application to the reviewer queue with a reason."""
        flag_for_review(backing, application_id, reason)

    @server.tool(name="log_event")
    def _log_event(application_id: str, event_type: str, payload: dict[str, object]) -> None:
        """Append an event to the audit log."""
        log_event(backing, application_id, event_type, payload)

    return server


if __name__ == "__main__":
    build_server().run()
