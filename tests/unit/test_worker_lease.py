import time
from uuid import uuid4

import pytest

from packages.worker.lease import (
    InMemoryLeaseManager,
    LeaseError,
    LeaseExpiredError,
    LeaseNotOwnedError,
)


def test_lease_acquire_heartbeat_release():
    manager = InMemoryLeaseManager(lease_seconds=5)
    task_id = uuid4()
    lease = manager.acquire(task_id, "worker-1")
    renewed = manager.heartbeat(lease)

    assert renewed.lease_id == lease.lease_id
    assert renewed.expires_at > renewed.heartbeat_at

    manager.release(renewed)
    assert manager.acquire(task_id, "worker-2").worker_id == "worker-2"


def test_second_worker_cannot_acquire_live_lease():
    manager = InMemoryLeaseManager(lease_seconds=5)
    task_id = uuid4()
    manager.acquire(task_id, "worker-1")

    with pytest.raises(LeaseError):
        manager.acquire(task_id, "worker-2")


def test_wrong_worker_cannot_heartbeat_or_release():
    manager = InMemoryLeaseManager(lease_seconds=5)
    lease = manager.acquire(uuid4(), "worker-1")
    impostor = lease.__class__(
        task_id=lease.task_id,
        worker_id="worker-2",
        lease_id=lease.lease_id,
        acquired_at=lease.acquired_at,
        expires_at=lease.expires_at,
        heartbeat_at=lease.heartbeat_at,
    )

    with pytest.raises(LeaseNotOwnedError):
        manager.heartbeat(impostor)
    with pytest.raises(LeaseNotOwnedError):
        manager.release(impostor)


def test_expired_lease_can_be_reclaimed():
    manager = InMemoryLeaseManager(lease_seconds=5)
    task_id = uuid4()
    lease = manager.acquire(task_id, "worker-1")
    expired = lease.__class__(
        task_id=lease.task_id,
        worker_id=lease.worker_id,
        lease_id=lease.lease_id,
        acquired_at=lease.acquired_at,
        expires_at=lease.acquired_at,
        heartbeat_at=lease.heartbeat_at,
    )
    manager._leases[task_id] = expired

    reclaimed = manager.acquire(task_id, "worker-2")
    assert reclaimed.worker_id == "worker-2"
