"""In-memory repository used for tests and local development."""

from copy import deepcopy
from uuid import UUID

from packages.domain.models import AuditEvent, Task
from packages.domain.repository import ConcurrentUpdateError, TaskNotFoundError


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[UUID, Task] = {}
        self._owners: dict[UUID, str | None] = {}
        self._audit: list[AuditEvent] = []

    def get(self, task_id: UUID) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(str(task_id))
        return deepcopy(task)

    def get_owned(self, task_id: UUID, owner_id: UUID) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(str(task_id))
        owner = self._owners.get(task_id)
        # Unowned tasks are supported only for legacy local/test fixtures.
        if owner is not None and owner != str(owner_id):
            raise TaskNotFoundError(str(task_id))
        return deepcopy(task)

    def list_tasks(self, *, limit: int = 50, owner_id: UUID | None = None) -> list[Task]:
        if limit < 1:
            raise ValueError("limit must be at least 1.")
        tasks = list(self._tasks.values())
        if owner_id is not None:
            tasks = [
                task for task in tasks
                if self._owners.get(task.task_id) in {None, str(owner_id)}
            ]
        return [deepcopy(task) for task in tasks[:limit]]

    def create(self, task: Task, *, owner_id: UUID | None = None) -> Task:
        if task.task_id in self._tasks:
            raise ConcurrentUpdateError(f"Task {task.task_id} already exists.")
        self._tasks[task.task_id] = deepcopy(task)
        self._owners[task.task_id] = str(owner_id) if owner_id is not None else None
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

    def find_by_approval_id(self, approval_id: UUID, *, owner_id: UUID | None = None) -> Task:
        for task in self._tasks.values():
            if owner_id is not None and self._owners.get(task.task_id) not in {None, str(owner_id)}:
                continue
            for action in task.actions:
                if action.approval_request and action.approval_request.approval_id == approval_id:
                    return deepcopy(task)
        raise TaskNotFoundError(str(approval_id))

    def list_pending_approvals(
        self, *, limit: int = 50, owner_id: UUID | None = None
    ) -> list[Task]:
        if limit < 1:
            raise ValueError("limit must be at least 1.")
        results: list[Task] = []
        for task in self._tasks.values():
            if owner_id is not None and self._owners.get(task.task_id) not in {None, str(owner_id)}:
                continue
            if task.status.value != "WAITING_APPROVAL":
                continue
            if any(
                action.approval_request and action.approval_request.status.value == "PENDING"
                for action in task.actions
            ):
                results.append(deepcopy(task))
            if len(results) >= limit:
                break
        return results

    def list_audit(self, task_id: UUID) -> list[AuditEvent]:
        return [deepcopy(e) for e in self._audit if e.task_id == task_id]

    def append_audit(self, event: AuditEvent) -> None:
        self._audit.append(deepcopy(event))

    def audit_events(self, task_id: UUID) -> list[AuditEvent]:
        return [deepcopy(e) for e in self._audit if e.task_id == task_id]
