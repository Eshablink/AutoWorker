from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from packages.domain.models import Task, TaskStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    goal: str = Field(min_length=5, max_length=10_000)


class TaskResponse(BaseModel):
    task_id: UUID
    goal: str
    status: TaskStatus
    version: int


_tasks: dict[UUID, Task] = {}


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(request: CreateTaskRequest) -> TaskResponse:
    task = Task(task_id=uuid4(), goal=request.goal)
    _tasks[task.task_id] = task
    return TaskResponse(
        task_id=task.task_id,
        goal=task.goal,
        status=task.status,
        version=task.version,
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: UUID) -> TaskResponse:
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return TaskResponse(
        task_id=task.task_id,
        goal=task.goal,
        status=task.status,
        version=task.version,
    )
