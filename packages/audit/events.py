"""Typed operational events for task execution streaming."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    TASK_CREATED = "TASK_CREATED"
    TASK_STATE_CHANGED = "TASK_STATE_CHANGED"
    ACTION_STARTED = "ACTION_STARTED"
    ACTION_COMPLETED = "ACTION_COMPLETED"
    ACTION_FAILED = "ACTION_FAILED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_DECIDED = "APPROVAL_DECIDED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    VERIFICATION_STARTED = "VERIFICATION_STARTED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"


class TaskEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EventBus:
    """Bounded in-process event bus; replaceable by Redis/Kafka later."""

    def __init__(self, *, max_events: int = 10_000) -> None:
        if max_events < 1:
            raise ValueError("max_events must be at least 1.")
        self.max_events = max_events
        self._events: list[TaskEvent] = []

    def publish(self, event: TaskEvent) -> TaskEvent:
        self._events.append(event)
        overflow = len(self._events) - self.max_events
        if overflow > 0:
            del self._events[:overflow]
        return event

    def list_for_task(self, task_id: UUID) -> list[TaskEvent]:
        return [event for event in self._events if event.task_id == task_id]
