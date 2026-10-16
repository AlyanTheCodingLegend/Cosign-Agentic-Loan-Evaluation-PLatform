"""MCP server and tool definitions."""

from mcp.server.mcpserver import MCPServer

from app.models.application import ApplicationInput
from app.models.contract import Metrics


def build_server() -> MCPServer:
    """Create the MCP server and register every tool."""
    raise NotImplementedError


def get_application(application_id: str) -> ApplicationInput:
    """Return the application with the given id."""
    raise NotImplementedError


def compute_metrics(application_id: str) -> Metrics:
    """Compute metrics for the application with the given id."""
    raise NotImplementedError


def request_info(application_id: str, question: str) -> None:
    """Ask the applicant a specific question and move the application to needs_info."""
    raise NotImplementedError


def flag_for_review(application_id: str, reason: str) -> None:
    """Send the application to the reviewer queue with a reason."""
    raise NotImplementedError


def log_event(application_id: str, event_type: str, payload: dict[str, object]) -> None:
    """Append an event to the audit log."""
    raise NotImplementedError
