"""Lease and heartbeat primitives for durable workers."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4


class LeaseError(RuntimeError):
    """Base lease failure."""


class LeaseNotOwnedError(LeaseError):
    """Raised when a worker attempts to renew/release another worker's lease."""


class LeaseExpiredError(LeaseError):
    """Raised when a lease is no longer valid."""


@dataclass(frozen=True)
class WorkerLease:
    task_id: UUID
    worker_id: str
    lease_id: UUID
    acquired_at: datetime
    expires_at: datetime
    heartbeat_at: datetime

    @property
    def expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


class InMemoryLeaseManager:
    """Reference lease implementation; production storage will be DB-backed."""

    def __init__(self, lease_seconds: int = 30) -> None:
        if lease_seconds < 5:
            raise ValueError("lease_seconds must be at least 5.")
        self.lease_seconds = lease_seconds
        self._leases: dict[UUID, WorkerLease] = {}

    def acquire(self, task_id: UUID, worker_id: str) -> WorkerLease:
        existing = self._leases.get(task_id)
        if existing and not existing.expired:
            raise LeaseError(f"Task {task_id} is already leased.")
        now = datetime.now(timezone.utc)
        lease = WorkerLease(
            task_id=task_id,
            worker_id=worker_id,
            lease_id=uuid4(),
            acquired_at=now,
            expires_at=now + timedelta(seconds=self.lease_seconds),
            heartbeat_at=now,
        )
        self._leases[task_id] = lease
        return lease

    def heartbeat(self, lease: WorkerLease) -> WorkerLease:
        current = self._leases.get(lease.task_id)
        if current is None or current.lease_id != lease.lease_id or current.worker_id != lease.worker_id:
            raise LeaseNotOwnedError(f"Worker does not own lease for task {lease.task_id}.")
        if current.expired:
            raise LeaseExpiredError(f"Lease for task {lease.task_id} has expired.")
        now = datetime.now(timezone.utc)
        renewed = WorkerLease(
            task_id=current.task_id,
            worker_id=current.worker_id,
            lease_id=current.lease_id,
            acquired_at=current.acquired_at,
            expires_at=now + timedelta(seconds=self.lease_seconds),
            heartbeat_at=now,
        )
        self._leases[lease.task_id] = renewed
        return renewed

    def release(self, lease: WorkerLease) -> None:
        current = self._leases.get(lease.task_id)
        if current is None or current.lease_id != lease.lease_id or current.worker_id != lease.worker_id:
            raise LeaseNotOwnedError(f"Worker does not own lease for task {lease.task_id}.")
        self._leases.pop(lease.task_id, None)
