from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.audit.events import EventType, TaskEvent
from packages.persistence.sqlalchemy import Base
from packages.persistence.coordination import (
    SqlAlchemyEventOutbox,
    SqlAlchemyIdempotencyStore,
    SqlAlchemyLeaseManager,
)
from packages.worker.execution import (
    IdempotencyInProgressError,
    ToolExecutionResult,
)
from packages.worker.lease import LeaseError


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def test_durable_idempotency_claim_and_completion(session_factory):
    store = SqlAlchemyIdempotencyStore(session_factory)
    key = "invoice-123"

    assert store.claim(key) is None
    with pytest.raises(IdempotencyInProgressError):
        store.claim(key)

    result = ToolExecutionResult(output={"posted": True}, observation="posted once")
    store.put(key, result)

    assert store.claim(key) == result
    assert store.get(key) == result


def test_durable_lease_prevents_double_claim(session_factory):
    store = SqlAlchemyLeaseManager(session_factory, lease_seconds=30)
    task_id = uuid4()

    first = store.acquire(task_id, "worker-a")
    with pytest.raises(LeaseError):
        store.acquire(task_id, "worker-b")

    store.release(first)
    second = store.acquire(task_id, "worker-b")
    assert second.worker_id == "worker-b"


def test_outbox_is_durable_and_retryable(session_factory):
    store = SqlAlchemyEventOutbox(session_factory)
    task_id = uuid4()
    event = TaskEvent(
        task_id=task_id,
        event_type=EventType.ACTION_COMPLETED,
        payload={"ok": True},
    )

    store.append(event)
    pending = store.claim_batch()
    assert [item.event_id for item in pending] == [event.event_id]

    store.mark_failed(event.event_id, "broker unavailable")
    assert store.claim_batch()[0].payload == {"ok": True}

    store.mark_published(event.event_id)
    assert store.claim_batch() == []


def test_sqlalchemy_lease_can_heartbeat(session_factory):
    store = SqlAlchemyLeaseManager(session_factory, lease_seconds=30)
    task_id = uuid4()
    lease = store.acquire(task_id, "worker-a")
    renewed = store.heartbeat(lease)
    assert renewed.expires_at > lease.expires_at


def test_event_bus_can_persist_events_to_outbox(session_factory):
    from packages.audit.events import EventBus

    store = SqlAlchemyEventOutbox(session_factory)
    bus = EventBus(durable_sink=store)
    event = TaskEvent(task_id=uuid4(), event_type=EventType.TASK_STATE_CHANGED)

    bus.publish(event)

    assert store.claim_batch(limit=10)[0].event_id == event.event_id


def test_two_workers_cannot_claim_same_durable_idempotency_key(session_factory):
    first_store = SqlAlchemyIdempotencyStore(session_factory)
    second_store = SqlAlchemyIdempotencyStore(session_factory)

    assert first_store.claim("shared-write-1") is None
    with pytest.raises(IdempotencyInProgressError):
        second_store.claim("shared-write-1")
