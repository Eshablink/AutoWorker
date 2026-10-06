import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

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
