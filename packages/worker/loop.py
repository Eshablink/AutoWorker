"""Long-running worker loop around the durable task runtime."""

from threading import Event
from time import sleep
from typing import Callable

from packages.worker.runtime import WorkerRuntime, WorkerRunResult


class WorkerLoop:
    """Poll the runtime until stopped, with bounded idle backoff."""

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
            result = self.run_once()
            if result is not None and on_result is not None:
                on_result(result)
            interval = self.idle_interval_seconds if result is None else self.poll_interval_seconds
            stop_event.wait(interval)
