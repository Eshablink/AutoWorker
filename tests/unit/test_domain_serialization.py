from packages.domain.models import Task, TaskStatus
from packages.domain.serialization import task_from_record, task_to_record


def test_task_serialization_round_trip():
    task = Task(goal="Process an invoice")
    task.status = TaskStatus.READY
    record = task_to_record(task)

    restored = task_from_record(record)

    assert restored.task_id == task.task_id
    assert restored.goal == task.goal
    assert restored.status == TaskStatus.READY
    assert restored.version == task.version
