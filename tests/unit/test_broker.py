from uuid import uuid4

import pytest

from packages.worker.broker import BrokerBackedTaskQueue, RedisStreamsTaskBroker


class FakeRedis:
    def __init__(self):
        self.groups = []
        self.entries = []
        self.acked = []

    def xgroup_create(self, stream, group, id, mkstream):
        self.groups.append((stream, group, id, mkstream))

    def xadd(self, stream, fields, maxlen, approximate):
        message_id = f"{len(self.entries) + 1}-0"
        self.entries.append((message_id, fields))
        return message_id

    def xautoclaim(self, stream, group, consumer, min_idle_time, start_id, count):
        return ["0-0", []]

    def xreadgroup(self, group, worker, streams, count, block):
        if not self.entries:
            return []
        message_id, fields = self.entries.pop(0)
        return [(next(iter(streams)), [(message_id, fields)])]

    def xack(self, stream, group, message_id):
        self.acked.append((stream, group, message_id))


def test_redis_streams_broker_publishes_and_consumes():
    redis = FakeRedis()
    broker = RedisStreamsTaskBroker(redis)
    task_id = uuid4()

    message_id = broker.publish(task_id)
    message = broker.consume("worker-a")

    assert message_id == "1-0"
    assert message is not None
    assert message.task_id == task_id

    broker.acknowledge(message)
    assert redis.acked == [("autoworker:tasks", "autoworkers", "1-0")]


def test_redis_streams_broker_rejects_empty_worker_id():
    broker = RedisStreamsTaskBroker(FakeRedis())
    with pytest.raises(ValueError):
        broker.consume("")


def test_broker_backed_queue_updates_durable_queue_then_publishes():
    class Queue:
        def __init__(self):
            self.enqueued = []

        def enqueue(self, task_id):
            self.enqueued.append(task_id)

    redis = FakeRedis()
    broker = RedisStreamsTaskBroker(redis)
    queue = BrokerBackedTaskQueue(Queue(), broker)
    task_id = uuid4()

    queue.enqueue(task_id)

    assert queue.durable_queue.enqueued == [task_id]
    assert len(redis.entries) == 1


def test_stale_pending_message_is_reclaimed():
    redis = FakeRedis()
    broker = RedisStreamsTaskBroker(redis)
    task_id = uuid4()
    broker.publish(task_id)
    message = broker.consume("worker-a")
    assert message is not None
    broker.acknowledge(message)


def test_worker_fleet_processes_and_acknowledges_runtime_result():
    from threading import Event
    from packages.domain.models import TaskStatus
    from packages.worker.fleet import WorkerFleet
    from packages.worker.runtime import WorkerRunResult

    class Runtime:
        def __init__(self):
            self.processed = []

        def run_task(self, task_id):
            self.processed.append(task_id)
            return WorkerRunResult(task_id, TaskStatus.COMPLETED, True, "verification")

    runtime = Runtime()
    redis = FakeRedis()
    broker = RedisStreamsTaskBroker(redis)
    fleet = WorkerFleet(runtime, broker, worker_id="worker-a")
    task_id = uuid4()
    broker.publish(task_id)

    stop_event = Event()

    def ack_and_stop(message):
        broker.acknowledge(message)
        stop_event.set()

    message = broker.consume("worker-a")
    assert message is not None
    result = fleet._process(message.task_id)
    assert result is not None
    assert runtime.processed == [task_id]
    ack_and_stop(message)
    assert stop_event.is_set()
