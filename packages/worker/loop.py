"""Long-running worker loop around the durable task runtime."""

from threading import Event
from typing import Callable
import logging
import time

from packages.worker.runtime import WorkerRuntime, WorkerRunResult

logger = logging.getLogger("autoworker.worker.loop")


class WorkerLoop:
    """Poll the runtime until stopped and survive transient runtime errors."""

    def __init__(
        self,
        runtime: WorkerRuntime,
        *,
        poll_interval_seconds: float = 1.0,
        idle_interval_seconds: float | None = None,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive.")
        self.runtime = runtime
        self.poll_interval_seconds = poll_interval_seconds
        self.idle_interval_seconds = idle_interval_seconds or poll_interval_seconds
        if self.idle_interval_seconds <= 0:
            raise ValueError("idle_interval_seconds must be positive.")

    def run_once(self) -> WorkerRunResult | None:
        return self.runtime.run_once()

    def run_forever(
        self,
        stop_event: Event,
        *,
        on_result: Callable[[WorkerRunResult], None] | None = None,
    ) -> None:
        while not stop_event.is_set():
            started = time.monotonic()
            try:
                result = self.run_once()
            except Exception:
                logger.exception("worker_loop_iteration_failed")
                result = None
                interval = min(self.idle_interval_seconds * 2, 10.0)
            else:
                interval = self.idle_interval_seconds if result is None else self.poll_interval_seconds

            if result is not None and on_result is not None:
                on_result(result)

            elapsed = time.monotonic() - started
            stop_event.wait(max(0.0, interval - elapsed))
