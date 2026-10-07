"""SQLAlchemy persistence adapter with normalized operational projections."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Integer, String, Text, select
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditRecord(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class ApprovalRecord(Base):
    __tablename__ = "approval_requests"

    approval_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action_id: Mapped[str] = mapped_column(String(36), nullable=False)
    policy_decision_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    tool_id: Mapped[str] = mapped_column(String(255), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExecutionIdempotencyRecord(Base):
    __tablename__ = "execution_idempotency"

    idempotency_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LeaseRecord(Base):
    __tablename__ = "task_leases"

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    worker_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    lease_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EventOutboxRecord(Base):
    __tablename__ = "event_outbox"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class SqlAlchemyTaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, task_id: UUID) -> Task:
        row = self.session.get(TaskRecord, str(task_id))
        if row is None:
            raise TaskNotFoundError(str(task_id))
        return task_from_record(row.payload)

    def list_tasks(self, *, limit: int = 50) -> list[Task]:
        if limit < 1:
            raise ValueError("limit must be at least 1.")
        rows = self.session.execute(
            select(TaskRecord).order_by(TaskRecord.created_at.desc()).limit(limit)
        ).scalars().all()
        return [task_from_record(row.payload) for row in rows]

    def create(self, task: Task) -> Task:
        if self.session.get(TaskRecord, str(task.task_id)) is not None:
            raise ConcurrentUpdateError(f"Task {task.task_id} already exists.")
        self.session.add(
            TaskRecord(
                task_id=str(task.task_id),
                version=task.version,
                payload=task_to_record(task),
                created_at=task.created_at,
            )
        )
        self._sync_approval_projection(task)
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
        self._sync_approval_projection(task)
        return task

    def _sync_approval_projection(self, task: Task) -> None:
        for action in task.actions:
            approval = action.approval_request
            if approval is None:
                continue

            approval_id = str(approval.approval_id)
            row = self.session.get(ApprovalRecord, approval_id)
            if row is None:
                row = ApprovalRecord(approval_id=approval_id)
                self.session.add(row)

            row.task_id = str(approval.task_id)
            row.action_id = str(approval.action_id)
            row.policy_decision_id = str(approval.policy_decision_id)
            row.status = approval.status.value
            row.tool_id = approval.tool_id
            row.risk_level = approval.risk_level.value
            row.expires_at = approval.expires_at
            row.created_at = approval.created_at
            row.decided_at = approval.decided_at

    def find_by_approval_id(self, approval_id: UUID) -> Task:
        row = self.session.get(ApprovalRecord, str(approval_id))
        if row is None:
            raise TaskNotFoundError(str(approval_id))
        return self.get(UUID(row.task_id))

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
