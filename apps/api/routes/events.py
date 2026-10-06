from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from apps.api.database import get_task_repository
from packages.domain.repository import TaskNotFoundError
from packages.persistence.sqlalchemy import SqlAlchemyTaskRepository

router = APIRouter(prefix="/tasks", tags=["events"])


@router.get("/{task_id}/events")
def list_task_events(
    task_id: UUID,
    repository: SqlAlchemyTaskRepository = Depends(get_task_repository),
):
    try:
        repository.get(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found.") from exc

    return {
        "task_id": str(task_id),
        "events": [event.model_dump(mode="json") for event in repository.list_audit(task_id)],
    }
