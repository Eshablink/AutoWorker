from uuid import UUID

from fastapi import APIRouter

from packages.audit.events import EventBus

router = APIRouter(prefix="/tasks", tags=["events"])
event_bus = EventBus()


@router.get("/{task_id}/events")
def list_task_events(task_id: UUID):
    return {
        "task_id": str(task_id),
        "events": [event.model_dump(mode="json") for event in event_bus.list_for_task(task_id)],
    }
