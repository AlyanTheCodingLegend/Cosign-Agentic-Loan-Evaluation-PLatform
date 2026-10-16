"""Storage interface for applications and the append-only logs, with an in-memory fake."""

import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Protocol

from app.config import get_settings
from app.models.application import (
    ApplicationInput,
    ApplicationRecord,
    AuditEvent,
    OverrideEntry,
)
from app.models.status import Status


class ApplicationNotFound(LookupError):
    """Raised when an application id does not exist."""


class Store(Protocol):
    """Everything the agent needs from storage. Logs can only be appended to and read."""

    def create_application(self, application_input: ApplicationInput) -> ApplicationRecord: ...

    def get_application(self, application_id: str) -> ApplicationRecord: ...

    def update_application(self, application_id: str, **columns: Any) -> ApplicationRecord: ...

    def append_event(self, event: AuditEvent) -> None: ...

    def list_events(self, application_id: str) -> list[AuditEvent]: ...

    def append_override(self, entry: OverrideEntry) -> None: ...

    def list_overrides(self) -> list[OverrideEntry]: ...


def _now() -> datetime:
    return datetime.now(UTC)


class InMemoryStore:
    """Dict-backed store for tests and local runs."""

    def __init__(self) -> None:
        self._applications: dict[str, ApplicationRecord] = {}
        self._events: list[AuditEvent] = []
        self._overrides: list[OverrideEntry] = []

    def create_application(self, application_input: ApplicationInput) -> ApplicationRecord:
        now = _now()
        record = ApplicationRecord(
            id=str(uuid.uuid4()),
            status=Status.SUBMITTED,
            input=application_input,
            created_at=now,
            updated_at=now,
        )
        self._applications[record.id] = record
        return record.model_copy(deep=True)

    def get_application(self, application_id: str) -> ApplicationRecord:
        try:
            return self._applications[application_id].model_copy(deep=True)
        except KeyError as exc:
            raise ApplicationNotFound(application_id) from exc

    def update_application(self, application_id: str, **columns: Any) -> ApplicationRecord:
        current = self.get_application(application_id)
        merged = {**dict(current), **columns, "updated_at": _now()}
        record = ApplicationRecord.model_validate(merged)
        self._applications[application_id] = record
        return record.model_copy(deep=True)

    def append_event(self, event: AuditEvent) -> None:
        self.get_application(event.application_id)
        self._events.append(event)

    def list_events(self, application_id: str) -> list[AuditEvent]:
        return [e for e in self._events if e.application_id == application_id]

    def append_override(self, entry: OverrideEntry) -> None:
        self.get_application(entry.application_id)
        self._overrides.append(entry)

    def list_overrides(self) -> list[OverrideEntry]:
        return list(self._overrides)


@lru_cache
def get_store() -> Store:
    """Return the process-wide store: in-memory when USE_FAKES is set, else Supabase."""
    if get_settings().use_fakes:
        return InMemoryStore()
    from app.db.supabase_store import SupabaseStore

    return SupabaseStore()
