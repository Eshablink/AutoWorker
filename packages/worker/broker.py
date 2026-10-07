"""External task dispatch broker contracts and Redis Streams adapter."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from packages.persistence.queue import TaskQueue


@dataclass(frozen=True)
class BrokerMessage:
    task_id: UUID
    message_id: str


class TaskBroker(Protocol):
    def publish(self, task_id: UUID) -> str:
        ...

    def consume(self, worker_id: str, *, block_ms: int = 1000) -> BrokerMessage | None:
        ...

    def acknowledge(self, message: BrokerMessage) -> None:
        ...


class RedisStreamsTaskBroker:
    """Redis Streams transport layered in front of the durable SQL task queue.

    The SQL queue remains the system-of-record for task dispatch state. Redis
    provides scalable delivery and consumer-group coordination between workers.
    """

    def __init__(
        self,
        redis_client,
        *,
        stream_name: str = "autoworker:tasks",
        group_name: str = "autoworkers",
    ) -> None:
        self.redis = redis_client
        self.stream_name = stream_name
        self.group_name = group_name
        self._ensure_group()

    def _ensure_group(self) -> None:
        try:
            self.redis.xgroup_create(
                self.stream_name,
                self.group_name,
                id="0-0",
                mkstream=True,
            )
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def publish(self, task_id: UUID) -> str:
        return self.redis.xadd(
            self.stream_name,
            {"task_id": str(task_id)},
            maxlen=10000,
            approximate=True,
        )

    def consume(self, worker_id: str, *, block_ms: int = 1000) -> BrokerMessage | None:
        if not worker_id.strip():
            raise ValueError("worker_id cannot be empty.")
        if block_ms < 1:
            raise ValueError("block_ms must be positive.")

        response = self.redis.xreadgroup(
            self.group_name,
            worker_id,
            {self.stream_name: ">"},
            count=1,
            block=block_ms,
        )
        if not response:
            return None

        _, messages = response[0]
        message_id, fields = messages[0]
        raw_task_id = fields.get("task_id")
        if raw_task_id is None:
            raise ValueError("Broker message is missing task_id.")
        if isinstance(raw_task_id, bytes):
            raw_task_id = raw_task_id.decode()

        return BrokerMessage(task_id=UUID(raw_task_id), message_id=message_id)

    def acknowledge(self, message: BrokerMessage) -> None:
        self.redis.xack(self.stream_name, self.group_name, message.message_id)


class BrokerBackedTaskQueue:
    """Task queue facade that keeps SQL state authoritative and publishes hints."""

    def __init__(self, durable_queue: TaskQueue, broker: TaskBroker) -> None:
        self.durable_queue = durable_queue
        self.broker = broker

    def enqueue(self, task_id: UUID) -> None:
        self.durable_queue.enqueue(task_id)
        self.broker.publish(task_id)
