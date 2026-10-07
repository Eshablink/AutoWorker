import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from datetime import timedelta

from packages.domain.models import AuditEvent, Task
from packages.domain.repository import ConcurrentUpdateError
from packages.persistence.sqlalchemy import Base, SqlAlchemyTaskRepository


@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield SqlAlchemyTaskRepository(session)
        session.rollback()


def audit(task):
    return AuditEvent(task_id=task.task_id, event_type="TEST", actor="pytest")


def test_sqlalchemy_repository_round_trip(repo):
    task = repo.create(Task(goal="Process invoice"))
    repo.session.commit()
    loaded = repo.get(task.task_id)
    assert loaded.goal == "Process invoice"


def test_sqlalchemy_repository_lists_newest_tasks_first(repo):
    older = Task(goal="Older operational task")
    newer = Task(goal="Newer operational task", created_at=older.created_at + timedelta(seconds=1), updated_at=older.updated_at + timedelta(seconds=1))
    repo.create(older)
    repo.create(newer)
    repo.session.commit()

    tasks = repo.list_tasks(limit=2)
    assert [task.task_id for task in tasks] == [newer.task_id, older.task_id]


def test_sqlalchemy_repository_rejects_stale_version(repo):
    task = repo.create(Task(goal="Process invoice"))
    repo.session.commit()
    loaded = repo.get(task.task_id)
    loaded.version = 2
    repo.save(loaded, audit(loaded), expected_version=1)
    repo.session.commit()

    stale = repo.get(task.task_id)
    with pytest.raises(ConcurrentUpdateError):
        repo.save(stale, audit(stale), expected_version=1)
