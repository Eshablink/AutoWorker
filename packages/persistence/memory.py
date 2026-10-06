"""In-memory repository used for tests and local development."""

from copy import deepcopy
from uuid import UUID

from packages.domain.models import AuditEvent, Task
from packages.domain.repository import ConcurrentUpdateError, TaskNotFoundError


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[UUID, Task] = {}
        self._audit: list[AuditEvent] = []

    def get(self, task_id: UUID) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(str(task_id))
        return deepcopy(task)

    def create(self, task: Task) -> Task:
        if task.task_id in self._tasks:
            raise ConcurrentUpdateError(f"Task {task.task_id} already exists.")
        self._tasks[task.task_id] = deepcopy(task)
        return deepcopy(task)

    def save(self, task: Task, audit_event: AuditEvent, *, expected_version: int) -> Task:
        current = self._tasks.get(task.task_id)
        if current is None:
            raise TaskNotFoundError(str(task.task_id))
        if current.version != expected_version:
            raise ConcurrentUpdateError(
                f"Expected task version {expected_version}, found {current.version}."
            )
        self._tasks[task.task_id] = deepcopy(task)
        self._audit.append(deepcopy(audit_event))
        return deepcopy(task)

    def find_by_approval_id(self, approval_id: UUID) -> Task:
        for task in self._tasks.values():
            for action in task.actions:
                if action.approval_request and action.approval_request.approval_id == approval_id:
                    return deepcopy(task)
        raise TaskNotFoundError(str(approval_id))

    def list_audit(self, task_id: UUID) -> list[AuditEvent]:
        return [deepcopy(e) for e in self._audit if e.task_id == task_id]

    def append_audit(self, event: AuditEvent) -> None:
        self._audit.append(deepcopy(event))

    def audit_events(self, task_id: UUID) -> list[AuditEvent]:
        return [deepcopy(e) for e in self._audit if e.task_id == task_id]
