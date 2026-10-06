"""Stable JSON serialization helpers for durable task persistence."""

from typing import Any

from packages.domain.models import Task


def task_to_record(task: Task) -> dict[str, Any]:
    """Convert a domain aggregate into a JSON-compatible persistence record."""
    return task.model_dump(mode="json")


def task_from_record(record: dict[str, Any]) -> Task:
    """Rehydrate a task aggregate from a persistence record."""
    return Task.model_validate(record)
