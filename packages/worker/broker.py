"""External task dispatch broker contracts and Redis Streams adapter."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from packages.observability.metrics import BROKER_OPERATIONS
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
        stale_idle_ms: int = 60_000,
        maxlen: int = 10_000,
    ) -> None:
        if not stream_name.strip():
            raise ValueError("stream_name cannot be empty.")
        if not group_name.strip():
            raise ValueError("group_name cannot be empty.")
        if stale_idle_ms < 1_000:
            raise ValueError("stale_idle_ms must be at least 1000 ms.")
        if maxlen < 100:
            raise ValueError("maxlen must be at least 100.")
        self.redis = redis_client
        self.stream_name = stream_name.strip()
        self.group_name = group_name.strip()
        self.stale_idle_ms = stale_idle_ms
        self.maxlen = maxlen
        self._ensure_group()

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        stream_name: str = "autoworker:tasks",
        group_name: str = "autoworkers",
        stale_idle_ms: int = 60_000,
        maxlen: int = 10_000,
    ) -> "RedisStreamsTaskBroker":
        try:
            from redis import Redis
        except ImportError as exc:
            raise RuntimeError(
                "Redis support is not installed. Install the redis dependency."
            ) from exc
        return cls(
            Redis.from_url(url, decode_responses=True),
            stream_name=stream_name,
            group_name=group_name,
            stale_idle_ms=stale_idle_ms,
            maxlen=maxlen,
        )

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

    @staticmethod
    def _message(message_id, fields: dict) -> BrokerMessage:
        raw_task_id = fields.get("task_id")
        if raw_task_id is None:
            raise ValueError("Broker message is missing task_id.")
        if isinstance(raw_task_id, bytes):
            raw_task_id = raw_task_id.decode()
        return BrokerMessage(task_id=UUID(str(raw_task_id)), message_id=str(message_id))

    def publish(self, task_id: UUID) -> str:
        try:
            message_id = self.redis.xadd(
                self.stream_name,
                {"task_id": str(task_id)},
                maxlen=self.maxlen,
                approximate=True,
            )
        except Exception:
            BROKER_OPERATIONS.labels("publish", "error").inc()
            raise
        BROKER_OPERATIONS.labels("publish", "success").inc()
        return str(message_id)

    def consume(self, worker_id: str, *, block_ms: int = 1000) -> BrokerMessage | None:
        if not worker_id.strip():
            raise ValueError("worker_id cannot be empty.")
        if block_ms < 1:
            raise ValueError("block_ms must be positive.")

        worker = worker_id.strip()
        try:
            claimed = self.redis.xautoclaim(
                self.stream_name,
                self.group_name,
                worker,
                min_idle_time=self.stale_idle_ms,
                start_id="0-0",
                count=1,
            )
            pending = claimed[1] if len(claimed) > 1 else []
            if pending:
                message = self._message(*pending[0])
                BROKER_OPERATIONS.labels("consume_reclaimed", "success").inc()
                return message

            response = self.redis.xreadgroup(
                self.group_name,
                worker,
                {self.stream_name: ">"},
                count=1,
                block=block_ms,
            )
            if not response:
                BROKER_OPERATIONS.labels("consume", "empty").inc()
                return None

            _, messages = response[0]
            message = self._message(*messages[0])
            BROKER_OPERATIONS.labels("consume", "success").inc()
            return message
        except Exception:
            BROKER_OPERATIONS.labels("consume", "error").inc()
            raise

    def acknowledge(self, message: BrokerMessage) -> None:
        try:
            self.redis.xack(self.stream_name, self.group_name, message.message_id)
        except Exception:
            BROKER_OPERATIONS.labels("acknowledge", "error").inc()
            raise
        BROKER_OPERATIONS.labels("acknowledge", "success").inc()


class BrokerBackedTaskQueue:
    """SQL-authoritative queue facade with Redis used as a low-latency dispatch hint."""

    def __init__(self, durable_queue: TaskQueue, broker: TaskBroker) -> None:
        self.durable_queue = durable_queue
        self.broker = broker

    def enqueue(self, task_id: UUID) -> str | None:
        self.durable_queue.enqueue(task_id)
        try:
            return self.broker.publish(task_id)
        except Exception:
            # SQL is authoritative. A failed broker hint must not make durable
            # task creation unavailable; a worker can recover the task by polling SQL.
            return None
