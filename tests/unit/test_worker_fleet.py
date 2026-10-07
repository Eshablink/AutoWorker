from threading import Event
from uuid import uuid4

from packages.domain.models import TaskStatus
from packages.worker.fleet import WorkerFleet
from packages.worker.runtime import WorkerRunResult


class FakeBroker:
    def consume(self, worker_id, *, block_ms=1000):
        return None

    def publish(self, task_id):
        return "1-0"

    def acknowledge(self, message):
        raise AssertionError("No broker message should be acknowledged.")


class FakeRuntime:
    def __init__(self, stop_event):
        self.stop_event = stop_event
        self.calls = 0

    def run_once(self):
        self.calls += 1
        self.stop_event.set()
        return WorkerRunResult(uuid4(), TaskStatus.COMPLETED, True, "verification")

    def run_task(self, task_id):
        raise AssertionError("No broker task expected.")


def test_worker_fleet_falls_back_to_durable_runtime_when_broker_is_idle():
    stop = Event()
    runtime = FakeRuntime(stop)
    fleet = WorkerFleet(runtime, FakeBroker(), worker_id="worker-a")

    fleet.run_forever(stop, block_ms=1, fallback_poll_interval_seconds=0.001)

    assert runtime.calls == 1
