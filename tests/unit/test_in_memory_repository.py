import pytest

from packages.domain.models import AuditEvent, Task
from packages.domain.repository import ConcurrentUpdateError
from packages.persistence.memory import InMemoryTaskRepository


def audit(task):
    return AuditEvent(task_id=task.task_id, event_type="TEST", actor="pytest")


def test_repository_round_trip_and_audit():
    repo = InMemoryTaskRepository()
    task = repo.create(Task(goal="Process invoice"))
    loaded = repo.get(task.task_id)
    assert loaded.task_id == task.task_id

    loaded.version = 2
    saved = repo.save(loaded, audit(loaded), expected_version=1)

    assert saved.version == 2
    assert len(repo.audit_events(task.task_id)) == 1


def test_repository_rejects_stale_version():
    repo = InMemoryTaskRepository()
    task = repo.create(Task(goal="Process invoice"))
    stale = repo.get(task.task_id)
    current = repo.get(task.task_id)
    current.version = 2
    repo.save(current, audit(current), expected_version=1)

    with pytest.raises(ConcurrentUpdateError):
        repo.save(stale, audit(stale), expected_version=1)


def test_repository_lists_tasks_with_limit():
    repo = InMemoryTaskRepository()
    repo.create(Task(goal="First invoice task"))
    repo.create(Task(goal="Second invoice task"))
    assert len(repo.list_tasks(limit=1)) == 1
