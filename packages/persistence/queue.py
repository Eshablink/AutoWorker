"""Durable task dispatch queue backed by SQLAlchemy."""

from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from packages.observability.metrics import DISPATCH_QUEUE_DEPTH, WORKER_QUEUE_CLAIMS
from packages.persistence.sqlalchemy import DispatchQueueRecord


class TaskQueue(Protocol):
    def enqueue(self, task_id: UUID, *, available_at: datetime | None = None) -> None:
        ...

    def claim_next(self, worker_id: str) -> UUID | None:
        ...

    def release(self, task_id: UUID, *, delay_seconds: float = 0, error: str | None = None) -> None:
        ...

    def block(self, task_id: UUID) -> None:
        ...

    def complete(self, task_id: UUID) -> None:
        ...


class SqlAlchemyTaskQueue:
    """PostgreSQL-safe dispatch queue.

    The queue is an execution hint; the task lease remains the authority that
    prevents concurrent workers from processing the same task.
    """

    READY = "READY"
    CLAIMED = "CLAIMED"
    BLOCKED = "BLOCKED"
    DONE = "DONE"

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def enqueue(self, task_id: UUID, *, available_at: datetime | None = None) -> None:
        when = available_at or datetime.now(timezone.utc)
        with self.session_factory() as session:
            row = session.get(DispatchQueueRecord, str(task_id))
            if row is None:
                session.add(
                    DispatchQueueRecord(
                        task_id=str(task_id),
                        state=self.READY,
                        available_at=when,
                        attempts=0,
                    )
                )
            else:
                row.state = self.READY
                row.available_at = when
                row.claimed_by = None
                row.claimed_at = None
                row.last_error = None
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise

    def claim_next(self, worker_id: str) -> UUID | None:
        now = datetime.now(timezone.utc)
        stale_before = now - timedelta(seconds=120)
        with self.session_factory() as session:
            session.execute(
                update(DispatchQueueRecord)
                .where(
                    DispatchQueueRecord.state == self.CLAIMED,
                    DispatchQueueRecord.claimed_at.is_not(None),
                    DispatchQueueRecord.claimed_at < stale_before,
                )
                .values(
                    state=self.READY,
                    claimed_by=None,
                    claimed_at=None,
                    available_at=now,
                    last_error="Recovered stale dispatch claim.",
                )
            )
            session.commit()
            stmt = (
                select(DispatchQueueRecord)
                .where(
                    DispatchQueueRecord.state == self.READY,
                    DispatchQueueRecord.available_at <= now,
                )
                .order_by(DispatchQueueRecord.available_at.asc())
                .limit(1)
            )
            if session.bind is not None and session.bind.dialect.name == "postgresql":
                stmt = stmt.with_for_update(skip_locked=True)

            row = session.execute(stmt).scalar_one_or_none()
            if row is None:
                WORKER_QUEUE_CLAIMS.labels("empty").inc()
                self._record_depth(session)
                return None

            row.state = self.CLAIMED
            row.claimed_by = worker_id
            row.claimed_at = now
            row.attempts += 1
            session.commit()
            WORKER_QUEUE_CLAIMS.labels("claimed").inc()
            self._record_depth(session)
            return UUID(row.task_id)

    def _record_depth(self, session: Session) -> None:
        depth = session.scalar(
            select(func.count()).select_from(DispatchQueueRecord).where(
                DispatchQueueRecord.state == self.READY
            )
        ) or 0
        DISPATCH_QUEUE_DEPTH.set(int(depth))

    def release(
        self,
        task_id: UUID,
        *,
        delay_seconds: float = 0,
        error: str | None = None,
    ) -> None:
        with self.session_factory() as session:
            session.execute(
                update(DispatchQueueRecord)
                .where(DispatchQueueRecord.task_id == str(task_id))
                .values(
                    state=self.READY,
                    available_at=datetime.now(timezone.utc) + timedelta(seconds=delay_seconds),
                    claimed_by=None,
                    claimed_at=None,
                    last_error=error,
                )
            )
            session.commit()
            self._record_depth(session)

    def block(self, task_id: UUID) -> None:
        with self.session_factory() as session:
            session.execute(
                update(DispatchQueueRecord)
                .where(DispatchQueueRecord.task_id == str(task_id))
                .values(state=self.BLOCKED, claimed_by=None, claimed_at=None)
            )
            session.commit()
            self._record_depth(session)

    def complete(self, task_id: UUID) -> None:
        with self.session_factory() as session:
            session.execute(
                update(DispatchQueueRecord)
                .where(DispatchQueueRecord.task_id == str(task_id))
                .values(
                    state=self.DONE,
                    completed_at=datetime.now(timezone.utc),
                    claimed_by=None,
                    claimed_at=None,
                )
            )
            session.commit()
            self._record_depth(session)

    def queue_depth(self) -> int:
        with self.session_factory() as session:
            depth = int(
                session.scalar(
                    select(func.count()).select_from(DispatchQueueRecord).where(
                        DispatchQueueRecord.state == self.READY
                    )
                ) or 0
            )
            DISPATCH_QUEUE_DEPTH.set(depth)
            return depth
