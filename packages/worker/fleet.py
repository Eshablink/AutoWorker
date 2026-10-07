"""Long-running worker fleet service around the AutoWorker runtime."""

import logging
import time
from threading import Event
from uuid import UUID

from packages.observability.metrics import BROKER_OPERATIONS
from packages.worker.broker import TaskBroker
from packages.worker.runtime import WorkerRunResult, WorkerRuntime

logger = logging.getLogger("autoworker.worker.fleet")


class WorkerFleet:
    """Consume Redis hints while falling back to the durable SQL queue.

    Redis is a low-latency delivery accelerator; the SQL dispatch queue and
    database leases remain the durable source of truth. The fallback poll means
    tasks remain executable when Redis is unavailable or a hint was missed.
    """

    def __init__(
        self,
        runtime: WorkerRuntime,
        broker: TaskBroker,
        *,
        worker_id: str,
    ) -> None:
        if not worker_id.strip():
            raise ValueError("worker_id cannot be empty.")
        self.runtime = runtime
        self.broker = broker
        self.worker_id = worker_id.strip()

    def run_forever(
        self,
        stop_event: Event,
        *,
        block_ms: int = 1000,
        fallback_poll_interval_seconds: float = 5.0,
        on_result=None,
    ) -> None:
        if block_ms < 1:
            raise ValueError("block_ms must be positive.")
        if fallback_poll_interval_seconds <= 0:
            raise ValueError("fallback_poll_interval_seconds must be positive.")

        next_fallback = time.monotonic()
        while not stop_event.is_set():
            message = None
            try:
                message = self.broker.consume(self.worker_id, block_ms=block_ms)
            except Exception:
                BROKER_OPERATIONS.labels("consume_loop", "error").inc()
                logger.exception(
                    "broker_consume_failed",
                    extra={"worker_id": self.worker_id, "outcome": "exception"},
                )

            if message is not None:
                BROKER_OPERATIONS.labels("delivery", "received").inc()
                try:
                    result = self._process(message.task_id)
                except Exception:
                    BROKER_OPERATIONS.labels("delivery", "processing_error").inc()
                    logger.exception(
                        "broker_task_processing_failed",
                        extra={
                            "worker_id": self.worker_id,
                            "task_id": str(message.task_id),
                            "broker_message_id": message.message_id,
                            "outcome": "exception",
                        },
                    )
                    # Do not ACK. Redis Streams will reclaim the pending message.
                    result = None
                if result is not None:
                    self.broker.acknowledge(message)
                    BROKER_OPERATIONS.labels("delivery", "acknowledged").inc()
                    if on_result is not None:
                        on_result(result)

            now = time.monotonic()
            if now >= next_fallback:
                try:
                    fallback_result = self.runtime.run_once()
                    if fallback_result is not None and on_result is not None:
                        on_result(fallback_result)
                except Exception:
                    logger.exception(
                        "durable_queue_poll_failed",
                        extra={"worker_id": self.worker_id, "outcome": "exception"},
                    )
                next_fallback = now + fallback_poll_interval_seconds

    def _process(self, task_id: UUID) -> WorkerRunResult | None:
        return self.runtime.run_task(task_id)
