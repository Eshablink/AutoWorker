"""Durable PostgreSQL/SQLAlchemy coordination stores for workers."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, sessionmaker

from packages.persistence.sqlalchemy import (
    EventOutboxRecord,
    ExecutionIdempotencyRecord,
    LeaseRecord,
)
from packages.worker.execution import (
    IdempotencyInProgressError,
    IdempotencyStore,
    ToolExecutionResult,
)
from packages.worker.lease import (
    LeaseError,
    LeaseManager,
    LeaseNotOwnedError,
    LeaseExpiredError,
    WorkerLease,
)
from packages.audit.events import TaskEvent


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SqlAlchemyIdempotencyStore(IdempotencyStore):
    """Database-backed idempotency claim/complete store.

    A claimed key stays in progress until a successful completion is recorded.
    This is intentionally conservative: an abandoned side-effect claim must be
    reconciled rather than automatically replayed and risk duplicating a write.
    """

    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def get(self, key: str) -> ToolExecutionResult | None:
        with self.session_factory() as session:
            row = session.get(ExecutionIdempotencyRecord, key)
            if row is None or row.status != self.COMPLETED:
                return None
            return ToolExecutionResult(
                output=dict(row.output or {}),
                observation=row.observation or "",
            )

    def claim(self, key: str) -> ToolExecutionResult | None:
        now = _utc_now()
        with self.session_factory() as session:
            existing = session.get(ExecutionIdempotencyRecord, key)
            if existing is None:
                session.add(
                    ExecutionIdempotencyRecord(
                        idempotency_key=key,
                        status=self.IN_PROGRESS,
                        created_at=now,
                    )
                )
                try:
                    session.commit()
                    return None
                except IntegrityError:
                    session.rollback()
                    existing = session.get(ExecutionIdempotencyRecord, key)

            if existing is None:
                raise RuntimeError("Idempotency claim could not be resolved.")
            if existing.status == self.COMPLETED:
                return ToolExecutionResult(
                    output=dict(existing.output or {}),
                    observation=existing.observation or "",
                )
            raise IdempotencyInProgressError(
                f"Idempotency key '{key}' is already claimed by another execution."
            )

    def put(self, key: str, result: ToolExecutionResult) -> None:
        now = _utc_now()
        with self.session_factory() as session:
            row = session.get(ExecutionIdempotencyRecord, key)
            if row is None:
                raise KeyError(f"Idempotency key '{key}' was never claimed.")
            if row.status == self.COMPLETED:
                return
            row.status = self.COMPLETED
            row.output = dict(result.output)
            row.observation = result.observation
            row.completed_at = now
            session.commit()


class SqlAlchemyLeaseManager(LeaseManager):
    """Database-backed task lease manager safe for multiple worker processes."""

    def __init__(self, session_factory: sessionmaker[Session], lease_seconds: int = 30) -> None:
        if lease_seconds < 5:
            raise ValueError("lease_seconds must be at least 5.")
        self.session_factory = session_factory
        self.lease_seconds = lease_seconds

    def acquire(self, task_id: UUID, worker_id: str) -> WorkerLease:
        now = _utc_now()
        lease_id = uuid4()
        expires_at = now + timedelta(seconds=self.lease_seconds)

        with self.session_factory() as session:
            row = LeaseRecord(
                task_id=str(task_id),
                worker_id=worker_id,
                lease_id=str(lease_id),
                acquired_at=now,
                expires_at=expires_at,
                heartbeat_at=now,
            )
            session.add(row)
            try:
                session.commit()
                return WorkerLease(
                    task_id=task_id,
                    worker_id=worker_id,
                    lease_id=lease_id,
                    acquired_at=now,
                    expires_at=expires_at,
                    heartbeat_at=now,
                )
            except IntegrityError:
                session.rollback()

            result = session.execute(
                update(LeaseRecord)
                .where(
                    LeaseRecord.task_id == str(task_id),
                    LeaseRecord.expires_at <= now,
                )
                .values(
                    worker_id=worker_id,
                    lease_id=str(lease_id),
                    acquired_at=now,
                    expires_at=expires_at,
                    heartbeat_at=now,
                )
            )
            if result.rowcount != 1:
                session.rollback()
                raise LeaseError(f"Task {task_id} is already leased.")
            session.commit()
            return WorkerLease(
                task_id=task_id,
                worker_id=worker_id,
                lease_id=lease_id,
                acquired_at=now,
                expires_at=expires_at,
                heartbeat_at=now,
            )

    def heartbeat(self, lease: WorkerLease) -> WorkerLease:
        now = _utc_now()
        expires_at = now + timedelta(seconds=self.lease_seconds)
        with self.session_factory() as session:
            result = session.execute(
                update(LeaseRecord)
                .where(
                    LeaseRecord.task_id == str(lease.task_id),
                    LeaseRecord.lease_id == str(lease.lease_id),
                    LeaseRecord.worker_id == lease.worker_id,
                    LeaseRecord.expires_at > now,
                )
                .values(expires_at=expires_at, heartbeat_at=now)
            )
            if result.rowcount != 1:
                session.rollback()
                raise LeaseNotOwnedError(
                    f"Worker does not own a live lease for task {lease.task_id}."
                )
            session.commit()
            return WorkerLease(
                task_id=lease.task_id,
                worker_id=lease.worker_id,
                lease_id=lease.lease_id,
                acquired_at=lease.acquired_at,
                expires_at=expires_at,
                heartbeat_at=now,
            )

    def release(self, lease: WorkerLease) -> None:
        with self.session_factory() as session:
            result = session.execute(
                delete(LeaseRecord).where(
                    LeaseRecord.task_id == str(lease.task_id),
                    LeaseRecord.lease_id == str(lease.lease_id),
                    LeaseRecord.worker_id == lease.worker_id,
                )
            )
            if result.rowcount != 1:
                session.rollback()
                if lease.expired:
                    raise LeaseExpiredError(f"Lease for task {lease.task_id} has expired.")
                raise LeaseNotOwnedError(f"Worker does not own lease for task {lease.task_id}.")
            session.commit()


class SqlAlchemyEventOutbox:
    """Durable append-only operational event outbox."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def append(self, event: TaskEvent) -> TaskEvent:
        with self.session_factory() as session:
            existing = session.get(EventOutboxRecord, str(event.event_id))
            if existing is None:
                session.add(
                    EventOutboxRecord(
                        event_id=str(event.event_id),
                        task_id=str(event.task_id),
                        action_id=str(event.action_id) if event.action_id else None,
                        event_type=event.event_type.value,
                        payload=event.payload,
                        created_at=event.created_at,
                    )
                )
                session.commit()
        return event

    def claim_batch(self, *, limit: int = 100) -> list[TaskEvent]:
        if limit < 1:
            raise ValueError("limit must be at least 1.")
        with self.session_factory() as session:
            rows = (
                session.execute(
                    select(EventOutboxRecord)
                    .where(EventOutboxRecord.published_at.is_(None))
                    .order_by(EventOutboxRecord.created_at.asc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            return [self._to_event(row) for row in rows]

    def mark_published(self, event_id: UUID) -> None:
        with self.session_factory() as session:
            session.execute(
                update(EventOutboxRecord)
                .where(
                    EventOutboxRecord.event_id == str(event_id),
                    EventOutboxRecord.published_at.is_(None),
                )
                .values(published_at=_utc_now(), last_error=None)
            )
            session.commit()

    def mark_failed(self, event_id: UUID, error: str) -> None:
        with self.session_factory() as session:
            session.execute(
                update(EventOutboxRecord)
                .where(EventOutboxRecord.event_id == str(event_id))
                .values(
                    attempts=EventOutboxRecord.attempts + 1,
                    last_error=error,
                )
            )
            session.commit()

    @staticmethod
    def _to_event(row: EventOutboxRecord) -> TaskEvent:
        return TaskEvent(
            event_id=UUID(row.event_id),
            task_id=UUID(row.task_id),
            action_id=UUID(row.action_id) if row.action_id else None,
            event_type=row.event_type,
            payload=dict(row.payload),
            created_at=row.created_at,
        )
