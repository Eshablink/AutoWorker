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
