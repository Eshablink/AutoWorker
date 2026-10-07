from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.database import get_task_repository
from apps.api.auth import require_api_auth
from packages.domain.repository import TaskNotFoundError
from packages.persistence.sqlalchemy import SqlAlchemyTaskRepository

router = APIRouter(prefix="/tasks", tags=["events"], dependencies=[Depends(require_api_auth)])


@router.get("/{task_id}/events")
def list_task_events(
    task_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    repository: SqlAlchemyTaskRepository = Depends(get_task_repository),
) -> dict:
    try:
        repository.get(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found.") from exc

    events = repository.list_audit(task_id)
    return {
        "task_id": str(task_id),
        "events": [event.model_dump(mode="json") for event in events[-limit:]],
    }
