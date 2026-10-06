from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from packages.domain.models import Task, TaskStatus
from packages.persistence.memory import InMemoryTaskRepository

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    goal: str = Field(min_length=5, max_length=10_000)


class TaskResponse(BaseModel):
    task_id: UUID
    goal: str
    status: TaskStatus
    version: int


_repository = InMemoryTaskRepository()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(request: CreateTaskRequest) -> TaskResponse:
    task = Task(task_id=uuid4(), goal=request.goal)
    _repository.create(task)
    return TaskResponse(
        task_id=task.task_id,
        goal=task.goal,
        status=task.status,
        version=task.version,
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: UUID) -> TaskResponse:
    try:
        task = _repository.get(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found.") from exc
    return TaskResponse(
        task_id=task.task_id,
        goal=task.goal,
        status=task.status,
        version=task.version,
    )
