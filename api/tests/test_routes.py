import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.agent.fake_model import FakeModelClient
from app.agent.reasoner import get_model_client
from app.db.store import InMemoryStore, get_store
from app.main import app
from app.models.status import Status

SEED_PATH = Path(__file__).resolve().parents[1] / "seed" / "demo_applicants.json"
DEMO = {e["key"]: e for e in json.loads(SEED_PATH.read_text(encoding="utf-8"))}


@pytest.fixture
def store() -> Iterator[InMemoryStore]:
    memory = InMemoryStore()
    app.dependency_overrides[get_store] = lambda: memory
    app.dependency_overrides[get_model_client] = lambda: FakeModelClient()
    yield memory
    app.dependency_overrides.clear()


@pytest.fixture
def client(store: InMemoryStore) -> TestClient:
    return TestClient(app)


def _submit(client: TestClient, key: str) -> str:
    response = client.post("/applications", json=DEMO[key]["input"])
    assert response.status_code == 202
    assert response.json()["status"] == "submitted"
    return str(response.json()["id"])


def test_submit_runs_pipeline_and_lands_in_queue(client: TestClient, store: InMemoryStore) -> None:
    application_id = _submit(client, "unaffordable_decline")

    record = store.get_application(application_id)
    assert record.status is Status.PENDING_REVIEW
    assert "application_submitted" in [e.event_type for e in store.list_events(application_id)]


def test_invalid_submission_is_rejected(client: TestClient) -> None:
    response = client.post("/applications", json={"form": {"annual_income": -5}})

    assert response.status_code == 422


def test_reply_flow(client: TestClient, store: InMemoryStore) -> None:
    application_id = _submit(client, "missing_annuity")
    assert store.get_application(application_id).status is Status.NEEDS_INFO

    response = client.post(
        f"/applications/{application_id}/reply", json=DEMO["missing_annuity"]["reply"]
    )

    assert response.status_code == 202
    assert store.get_application(application_id).status is Status.AUTO_CLEARED


def test_reply_when_not_waiting_is_conflict(client: TestClient) -> None:
    application_id = _submit(client, "unaffordable_decline")

    response = client.post(f"/applications/{application_id}/reply", json={"answer": "hello"})

    assert response.status_code == 409


def test_reply_to_unknown_application_is_404(client: TestClient) -> None:
    response = client.post("/applications/nope/reply", json={"answer": "hello"})

    assert response.status_code == 404


def _decision(client: TestClient, application_id: str, body: dict[str, Any]) -> Any:
    return client.post(f"/applications/{application_id}/decision", json=body)


@pytest.mark.parametrize(
    "body",
    [
        {"reviewer_id": "r1", "action": "reject"},
        {"reviewer_id": "r1", "action": "reject", "reason": "   "},
        {"reviewer_id": "r1", "action": "override", "final_decision": "approve"},
        {"reviewer_id": "r1", "action": "override", "reason": "because"},
    ],
)
def test_reject_and_override_without_reason_are_validation_errors(
    client: TestClient, store: InMemoryStore, body: dict[str, Any]
) -> None:
    application_id = _submit(client, "unaffordable_decline")

    response = _decision(client, application_id, body)

    assert response.status_code == 422
    assert store.get_application(application_id).status is Status.PENDING_REVIEW


def test_override_decision_is_stored(client: TestClient, store: InMemoryStore) -> None:
    application_id = _submit(client, "unaffordable_decline")

    response = _decision(
        client,
        application_id,
        {
            "reviewer_id": "r1",
            "action": "override",
            "final_decision": "approve",
            "reason": "Co-signer",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": application_id,
        "status": "decided",
        "final_decision": "approve",
    }
    assert len(store.list_overrides()) == 1


def test_approving_a_decline_without_override_is_conflict(client: TestClient) -> None:
    application_id = _submit(client, "unaffordable_decline")

    response = _decision(client, application_id, {"reviewer_id": "r1", "action": "approve"})

    assert response.status_code == 409


def test_deciding_twice_is_conflict(client: TestClient) -> None:
    application_id = _submit(client, "borderline_refer")
    body = {"reviewer_id": "r1", "action": "approve"}
    assert _decision(client, application_id, body).status_code == 200

    assert _decision(client, application_id, body).status_code == 409


def test_decision_on_unknown_application_is_404(client: TestClient) -> None:
    assert _decision(client, "nope", {"reviewer_id": "r1", "action": "approve"}).status_code == 404
