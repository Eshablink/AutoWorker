"""AutoWorker worker process and composition root."""

from __future__ import annotations

import logging
import os
from threading import Event

from apps.api.database import get_session_factory, get_settings
from packages.persistence.coordination import SqlAlchemyIdempotencyStore, SqlAlchemyLeaseManager
from packages.persistence.queue import SqlAlchemyTaskQueue
from packages.policy.engine import PolicyEngine
from packages.worker.demo import build_demo_components
from packages.worker.fleet import WorkerFleet
from packages.worker.loop import WorkerLoop
from packages.worker.orchestrator import TaskOrchestrator
from packages.worker.runtime import WorkerRuntime

logger = logging.getLogger("autoworker.worker.main")


def build_runtime() -> WorkerRuntime:
    settings = get_settings()
    session_factory = get_session_factory()
    repository = __import__(
        "packages.persistence.sqlalchemy",
        fromlist=["SqlAlchemyTaskRepository"],
    ).SqlAlchemyTaskRepository(session_factory())

    registry, planner, executor, checks = build_demo_components()
    idempotency = SqlAlchemyIdempotencyStore(session_factory)
    lease_manager = SqlAlchemyLeaseManager(session_factory)
    orchestrator = TaskOrchestrator(
        registry,
        PolicyEngine(registry),
        __import__(
            "packages.worker.execution",
            fromlist=["ExecutionWorker"],
        ).ExecutionWorker(executor, idempotency),
    )
    return WorkerRuntime(
        repository,
        planner,
        orchestrator,
        lease_manager=lease_manager,
        verification_checks=lambda _task: checks,
        worker_id=os.getenv("AUTOWORKER_WORKER_ID", "autoworker-worker"),
        task_queue=SqlAlchemyTaskQueue(session_factory),
        lease_seconds=30,
    )


def run_worker(stop_event: Event | None = None) -> None:
    stop_event = stop_event or Event()
    settings = get_settings()
    runtime = build_runtime()

    if settings.redis_url:
        from packages.worker.broker import RedisStreamsTaskBroker

        broker = RedisStreamsTaskBroker.from_url(
            settings.redis_url,
            stream_name=settings.redis_stream_name,
            group_name=settings.redis_group_name,
            stale_idle_ms=settings.redis_stale_idle_ms,
            maxlen=settings.redis_maxlen,
        )
        WorkerFleet(
            runtime,
            broker,
            worker_id=os.getenv("AUTOWORKER_WORKER_ID", "autoworker-worker"),
        ).run_forever(
            stop_event,
            block_ms=settings.redis_block_ms,
        )
    else:
        WorkerLoop(runtime).run_forever(stop_event)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_worker()
