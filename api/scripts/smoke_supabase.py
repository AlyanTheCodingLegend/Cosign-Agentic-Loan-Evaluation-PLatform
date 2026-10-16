"""Run the pipeline against the real Supabase project and report pass or fail per step.

Usage (from api/, venv active, .env filled in):
    python scripts/smoke_supabase.py

Uses the real SupabaseStore and the rule-based fake model, so it checks the database path
without needing a model endpoint. It leaves demo rows behind: the audit log is append-only by
design, so test rows cannot be deleted.
"""

import json
import sys
from collections.abc import Callable
from pathlib import Path

from app.agent.fake_model import FakeModelClient
from app.agent.pipeline import apply_decision, apply_reply, run_pipeline
from app.db.client import get_client
from app.db.supabase_store import SupabaseStore
from app.models.application import (
    ApplicationInput,
    DecisionAction,
    DecisionRequest,
    FinalDecision,
    ReplyRequest,
)
from app.models.status import Status

SEED = Path(__file__).resolve().parents[1] / "seed" / "demo_applicants.json"
DEMO = {e["key"]: e for e in json.loads(SEED.read_text(encoding="utf-8"))}
RESULTS: list[tuple[str, bool, str]] = []


def step(name: str) -> Callable[[Callable[[], str]], Callable[[], str]]:
    """Register a check: it passes if it returns normally, fails on any exception."""

    def decorator(fn: Callable[[], str]) -> Callable[[], str]:
        try:
            RESULTS.append((name, True, fn()))
        except Exception as exc:
            RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
        return fn

    return decorator


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


store = SupabaseStore()
model = FakeModelClient()
state: dict[str, str] = {}


@step("connect and read the applications table")
def _connect() -> str:
    store._client.table("applications").select("id").limit(1).execute()
    return "ok"


@step("create an application and read it back")
def _create() -> str:
    entry = DEMO["unaffordable_decline"]
    record = store.create_application(ApplicationInput.model_validate(entry["input"]))
    state["decline"] = record.id
    fetched = store.get_application(record.id)
    _expect(fetched.status is Status.SUBMITTED, f"status {fetched.status}")
    _expect(fetched.input.form.annuity == entry["input"]["form"]["annuity"], "input mismatch")
    return record.id


@step("run the pipeline to pending_review with fields, metrics and output stored")
def _pipeline() -> str:
    status = run_pipeline(state["decline"], store, model)
    record = store.get_application(state["decline"])
    _expect(status is Status.PENDING_REVIEW, f"status {status}")
    _expect(record.fields is not None and record.metrics is not None, "fields or metrics missing")
    _expect(record.agent_output is not None, "agent_output missing")
    assert record.agent_output is not None
    return f"recommendation={record.agent_output.recommendation}"


@step("audit log has the status changes in order")
def _audit() -> str:
    events = store.list_events(state["decline"])
    changes = [
        (e.payload["from"], e.payload["to"]) for e in events if e.event_type == "status_changed"
    ]
    _expect(changes == [("submitted", "analyzing"), ("analyzing", "pending_review")], str(changes))
    return f"{len(events)} events"


@step("audit_log rejects update and delete")
def _append_only() -> str:
    client = get_client()
    outcomes = []
    for label, action in (
        (
            "update",
            lambda: (
                client.table("audit_log")
                .update({"actor": "x"})
                .eq("application_id", state["decline"])
            ),
        ),
        (
            "delete",
            lambda: client.table("audit_log").delete().eq("application_id", state["decline"]),
        ),
    ):
        try:
            action().execute()
        except Exception as exc:
            outcomes.append(f"{label} blocked ({type(exc).__name__})")
        else:
            raise AssertionError(f"{label} on audit_log was allowed")
    return ", ".join(outcomes)


@step("override decision lands in override_log with reviewer and reason")
def _override() -> str:
    record = apply_decision(
        state["decline"],
        DecisionRequest(
            reviewer_id="smoke-reviewer",
            action=DecisionAction.OVERRIDE,
            final_decision=FinalDecision.APPROVE,
            reason="Smoke test override",
        ),
        store,
    )
    _expect(record.status is Status.DECIDED, f"status {record.status}")
    _expect(record.final_decision is FinalDecision.APPROVE, "final_decision not stored")
    mine = [o for o in store.list_overrides() if o.application_id == state["decline"]]
    _expect(len(mine) == 1 and mine[0].reviewer_id == "smoke-reviewer", str(mine))
    return f"agent said {mine[0].agent_recommendation}, human said {mine[0].human_decision}"


@step("needs_info then reply resumes to auto_cleared")
def _reply_flow() -> str:
    entry = DEMO["missing_annuity"]
    record = store.create_application(ApplicationInput.model_validate(entry["input"]))
    first = run_pipeline(record.id, store, model)
    _expect(first is Status.NEEDS_INFO, f"first run {first}")
    _expect(bool(store.get_application(record.id).human_question), "human_question missing")
    apply_reply(record.id, ReplyRequest.model_validate(entry["reply"]), store)
    second = run_pipeline(record.id, store, model)
    _expect(second is Status.AUTO_CLEARED, f"second run {second}")
    _expect(store.get_application(record.id).human_question is None, "question not cleared")
    return "needs_info -> analyzing -> auto_cleared"


def main() -> int:
    """Print one line per step and return a non-zero exit code if any failed."""
    for name, passed, detail in RESULTS:
        print(f"{'PASS' if passed else 'FAIL'}  {name}  [{detail}]")
    failed = sum(not passed for _, passed, _ in RESULTS)
    print(f"\n{len(RESULTS) - failed}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
