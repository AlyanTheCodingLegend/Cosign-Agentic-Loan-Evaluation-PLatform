"""The single place that calls the model and validates its output against the contract."""

from app.models.contract import ReasonerInput, ReasonerOutput


def build_prompt(inp: ReasonerInput) -> str:
    """Build the reasoner prompt from fields and precomputed metrics, without protected data."""
    raise NotImplementedError


def recommend(inp: ReasonerInput) -> ReasonerOutput:
    """Call the model, retry once on failure, and fall back to refer with needs_human."""
    raise NotImplementedError
