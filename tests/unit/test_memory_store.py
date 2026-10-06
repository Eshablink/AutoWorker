from uuid import uuid4

from packages.memory.contracts import MemoryItem
from packages.memory.in_memory import InMemoryMemoryStore


def test_memory_store_round_trip_and_task_scoping():
    store = InMemoryMemoryStore()
    task_id = uuid4()
    item = store.put(
        MemoryItem(
            task_id=task_id,
            namespace="invoice",
            key="vendor",
            value={"name": "Acme"},
            importance=0.9,
        )
    )
    assert store.get(task_id, "invoice", "vendor").value["name"] == "Acme"
    assert store.search(task_id, "invoice", "acme")[0].memory_id == item.memory_id
    assert store.get(uuid4(), "invoice", "vendor") is None


def test_memory_search_validates_limit():
    store = InMemoryMemoryStore()
    try:
        store.search(uuid4(), "task", "anything", limit=0)
    except ValueError as exc:
        assert "at least 1" in str(exc)
    else:
        raise AssertionError("Expected invalid limit to fail")
