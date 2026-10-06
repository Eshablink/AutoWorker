"""SQLAlchemy persistence adapter skeleton.

Keeps database concerns outside the domain. The concrete schema intentionally
stores the complete Task aggregate as JSON until normalized projections are needed.
"""

from uuid import UUID

from sqlalchemy import JSON, Integer, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from packages.domain.models import AuditEvent, Task
from packages.domain.repository import ConcurrentUpdateError, TaskNotFoundError
from packages.domain.serialization import task_from_record, task_to_record


class Base(DeclarativeBase):
    pass


class TaskRecord(Base):
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class AuditRecord(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class SqlAlchemyTaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, task_id: UUID) -> Task:
        row = self.session.get(TaskRecord, str(task_id))
        if row is None:
            raise TaskNotFoundError(str(task_id))
        return task_from_record(row.payload)

    def create(self, task: Task) -> Task:
        if self.session.get(TaskRecord, str(task.task_id)) is not None:
            raise ConcurrentUpdateError(f"Task {task.task_id} already exists.")
        self.session.add(
            TaskRecord(
                task_id=str(task.task_id),
                version=task.version,
                payload=task_to_record(task),
            )
        )
        return task

    def save(self, task: Task, audit_event: AuditEvent, *, expected_version: int) -> Task:
        row = self.session.execute(
            select(TaskRecord).where(
                TaskRecord.task_id == str(task.task_id),
                TaskRecord.version == expected_version,
            )
        ).scalar_one_or_none()
        if row is None:
            raise ConcurrentUpdateError(
                f"Task {task.task_id} is missing or has a different version."
            )
        row.version = task.version
        row.payload = task_to_record(task)
        self.session.add(
            AuditRecord(
                event_id=str(audit_event.event_id),
                task_id=str(audit_event.task_id),
                payload=audit_event.model_dump(mode="json"),
            )
        )
        return task

    def find_by_approval_id(self, approval_id: UUID) -> Task:
        rows = self.session.execute(select(TaskRecord)).scalars().all()
        for row in rows:
            task = task_from_record(row.payload)
            if any(action.approval_request and action.approval_request.approval_id == approval_id for action in task.actions):
                return task
        raise TaskNotFoundError(str(approval_id))

    def list_audit(self, task_id: UUID) -> list[AuditEvent]:
        rows = self.session.execute(
            select(AuditRecord).where(AuditRecord.task_id == str(task_id))
        ).scalars().all()
        events = [AuditEvent.model_validate(row.payload) for row in rows]
        return sorted(events, key=lambda event: event.timestamp)

    def append_audit(self, event: AuditEvent) -> None:
        self.session.add(
            AuditRecord(
                event_id=str(event.event_id),
                task_id=str(event.task_id),
                payload=event.model_dump(mode="json"),
            )
        )
