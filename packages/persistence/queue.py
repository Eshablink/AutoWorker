"""Durable task dispatch queue backed by SQLAlchemy."""

from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

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
        with self.session_factory() as session:
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
                return None

            row.state = self.CLAIMED
            row.claimed_by = worker_id
            row.claimed_at = now
            row.attempts += 1
            session.commit()
            return UUID(row.task_id)

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

    def block(self, task_id: UUID) -> None:
        with self.session_factory() as session:
            session.execute(
                update(DispatchQueueRecord)
                .where(DispatchQueueRecord.task_id == str(task_id))
                .values(state=self.BLOCKED, claimed_by=None, claimed_at=None)
            )
            session.commit()

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

    def queue_depth(self) -> int:
        with self.session_factory() as session:
            return int(
                session.execute(
                    select(DispatchQueueRecord.task_id).where(
                        DispatchQueueRecord.state == self.READY
                    )
                ).scalars().count()
            )
