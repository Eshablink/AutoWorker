from uuid import uuid4

from packages.audit.events import EventBus, EventType, TaskEvent


def test_event_bus_preserves_task_events():
    task_id = uuid4()
    bus = EventBus()
    bus.publish(TaskEvent(task_id=task_id, event_type=EventType.TASK_CREATED))
    bus.publish(TaskEvent(task_id=task_id, event_type=EventType.ACTION_STARTED))

    events = bus.list_for_task(task_id)

    assert [event.event_type for event in events] == [
        EventType.TASK_CREATED,
        EventType.ACTION_STARTED,
    ]


def test_event_bus_evicts_oldest_events_when_capacity_is_reached():
    task_id = uuid4()
    bus = EventBus(max_events=2)
    first = bus.publish(TaskEvent(task_id=task_id, event_type=EventType.TASK_CREATED))
    bus.publish(TaskEvent(task_id=task_id, event_type=EventType.ACTION_STARTED))
    bus.publish(TaskEvent(task_id=task_id, event_type=EventType.ACTION_COMPLETED))

    events = bus.list_for_task(task_id)
    assert first not in events
    assert [event.event_type for event in events] == [
        EventType.ACTION_STARTED,
        EventType.ACTION_COMPLETED,
    ]


def test_event_bus_requires_positive_capacity():
    import pytest

    with pytest.raises(ValueError, match="at least 1"):
        EventBus(max_events=0)
