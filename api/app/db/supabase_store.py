"""Supabase-backed Store. The logs are insert-only here and blocked from mutation by triggers."""

import json
from typing import Any

from supabase import Client

from app.db.client import get_client
from app.db.store import ApplicationNotFound
from app.models.application import (
    ApplicationInput,
    ApplicationRecord,
    AuditEvent,
    OverrideEntry,
)


def _encode(value: object) -> object:
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _jsonable(columns: dict[str, Any]) -> dict[str, Any]:
    """Convert pydantic models, enums and datetimes to plain JSON values."""
    result: dict[str, Any] = json.loads(json.dumps(columns, default=_encode))
    return result


class SupabaseStore:
    """Store backed by the tables in db/schema.sql."""

    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_client()

    def create_application(self, application_input: ApplicationInput) -> ApplicationRecord:
        row = _jsonable({"input": application_input})
        response = self._client.table("applications").insert(row).execute()
        return ApplicationRecord.model_validate(response.data[0])

    def get_application(self, application_id: str) -> ApplicationRecord:
        response = self._client.table("applications").select("*").eq("id", application_id).execute()
        if not response.data:
            raise ApplicationNotFound(application_id)
        return ApplicationRecord.model_validate(response.data[0])

    def update_application(self, application_id: str, **columns: Any) -> ApplicationRecord:
        response = (
            self._client.table("applications")
            .update(_jsonable(columns))
            .eq("id", application_id)
            .execute()
        )
        if not response.data:
            raise ApplicationNotFound(application_id)
        return ApplicationRecord.model_validate(response.data[0])

    def append_event(self, event: AuditEvent) -> None:
        row = _jsonable(event.model_dump(exclude={"created_at"}))
        self._client.table("audit_log").insert(row).execute()

    def list_events(self, application_id: str) -> list[AuditEvent]:
        response = (
            self._client.table("audit_log")
            .select("*")
            .eq("application_id", application_id)
            .order("id")
            .execute()
        )
        return [AuditEvent.model_validate(row) for row in response.data]

    def append_override(self, entry: OverrideEntry) -> None:
        row = _jsonable(entry.model_dump(exclude={"created_at"}))
        self._client.table("override_log").insert(row).execute()

    def list_overrides(self) -> list[OverrideEntry]:
        response = self._client.table("override_log").select("*").order("id").execute()
        return [OverrideEntry.model_validate(row) for row in response.data]
