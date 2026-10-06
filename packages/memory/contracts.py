"""Task-scoped memory contracts with explicit retention semantics."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class MemoryItem:
    memory_id: UUID = field(default_factory=uuid4)
    task_id: UUID | None = None
    namespace: str = "task"
    key: str = ""
    value: dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    created_at: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None


class MemoryStore(Protocol):
    def put(self, item: MemoryItem) -> MemoryItem:
        ...

    def get(self, task_id: UUID, namespace: str, key: str) -> MemoryItem | None:
        ...

    def search(self, task_id: UUID, namespace: str, query: str, *, limit: int = 10) -> list[MemoryItem]:
        ...

    def delete(self, memory_id: UUID) -> None:
        ...
