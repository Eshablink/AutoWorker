"""Reference memory store for tests and local execution."""

from copy import deepcopy
from uuid import UUID

from packages.memory.contracts import MemoryItem


class InMemoryMemoryStore:
    def __init__(self) -> None:
        self._items: dict[UUID, MemoryItem] = {}

    def put(self, item: MemoryItem) -> MemoryItem:
        if not 0.0 <= item.importance <= 1.0:
            raise ValueError("Memory importance must be between 0 and 1.")
        self._items[item.memory_id] = deepcopy(item)
        return deepcopy(item)

    def get(self, task_id: UUID, namespace: str, key: str) -> MemoryItem | None:
        for item in self._items.values():
            if item.task_id == task_id and item.namespace == namespace and item.key == key:
                return deepcopy(item)
        return None

    def search(self, task_id: UUID, namespace: str, query: str, *, limit: int = 10) -> list[MemoryItem]:
        if limit < 1:
            raise ValueError("limit must be at least 1.")
        needle = query.strip().lower()
        matches = [
            item for item in self._items.values()
            if item.task_id == task_id
            and item.namespace == namespace
            and needle in (item.key + " " + str(item.value)).lower()
        ]
        return [deepcopy(item) for item in matches[:limit]]

    def delete(self, memory_id: UUID) -> None:
        self._items.pop(memory_id, None)
