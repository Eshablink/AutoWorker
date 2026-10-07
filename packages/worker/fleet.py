"""Long-running worker fleet service around the AutoWorker runtime."""

from threading import Event
from uuid import UUID

from packages.worker.broker import TaskBroker
from packages.worker.runtime import WorkerRunResult, WorkerRuntime


class WorkerFleet:
    """Run workers from an external broker while retaining durable task state."""

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

    def run_forever(self, stop_event: Event, *, block_ms: int = 1000) -> None:
        while not stop_event.is_set():
            message = self.broker.consume(self.worker_id, block_ms=block_ms)
            if message is None:
                continue

            result = self._process(message.task_id)
            if result is not None:
                self.broker.acknowledge(message)

    def _process(self, task_id: UUID) -> WorkerRunResult | None:
        lease = self.runtime.lease_manager.acquire(task_id, self.worker_id)
        try:
            task = self.runtime.repository.get(task_id)
            return self.runtime._run_task(task)
        finally:
            self.runtime.lease_manager.release(lease)
