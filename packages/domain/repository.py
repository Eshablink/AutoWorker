"""Persistence boundary types for the AutoWorker domain.

The domain depends on this protocol, never on SQLAlchemy or PostgreSQL directly.
"""

from typing import Protocol
from uuid import UUID

from packages.domain.models import AuditEvent, Task


class ConcurrentUpdateError(RuntimeError):
    """Raised when optimistic concurrency detects a stale task version."""


class TaskNotFoundError(KeyError):
    """Raised when a task cannot be found."""


class TaskRepository(Protocol):
    def get(self, task_id: UUID) -> Task:
        ...

    def list_tasks(self, *, limit: int = 50) -> list[Task]:
        ...

    def create(self, task: Task) -> Task:
        ...

    def save(self, task: Task, audit_event: AuditEvent, *, expected_version: int) -> Task:
        """Persist atomically if expected_version matches the stored version."""
        ...

    def find_by_approval_id(self, approval_id: UUID) -> Task:
        ...

    def list_audit(self, task_id: UUID) -> list[AuditEvent]:
        ...

    def append_audit(self, event: AuditEvent) -> None:
        ...
