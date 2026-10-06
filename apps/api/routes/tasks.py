from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from packages.domain.models import Task, TaskStatus
from packages.domain.repository import TaskNotFoundError
from apps.api.database import get_task_repository
from packages.persistence.sqlalchemy import SqlAlchemyTaskRepository

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    goal: str = Field(min_length=5, max_length=10_000)


class TaskResponse(BaseModel):
    task_id: UUID
    goal: str
    status: TaskStatus
    version: int




@router.get("", response_model=list[TaskResponse])
def list_tasks(
    limit: int = Query(default=50, ge=1, le=100),
    repository: SqlAlchemyTaskRepository = Depends(get_task_repository),
) -> list[TaskResponse]:
    tasks = repository.list_tasks(limit=limit)
    return [
        TaskResponse(
            task_id=task.task_id,
            goal=task.goal,
            status=task.status,
            version=task.version,
        )
        for task in tasks
    ]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(request: CreateTaskRequest, repository: SqlAlchemyTaskRepository = Depends(get_task_repository)) -> TaskResponse:
    task = Task(task_id=uuid4(), goal=request.goal)
    repository.create(task)
    return TaskResponse(
        task_id=task.task_id,
        goal=task.goal,
        status=task.status,
        version=task.version,
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: UUID, repository: SqlAlchemyTaskRepository = Depends(get_task_repository)) -> TaskResponse:
    try:
        task = repository.get(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found.") from exc
    return TaskResponse(
        task_id=task.task_id,
        goal=task.goal,
        status=task.status,
        version=task.version,
    )
