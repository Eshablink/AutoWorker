from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from apps.api.database import get_task_broker, get_task_repository
from packages.domain.models import AuditEvent, Task, TaskStatus
from packages.domain.repository import TaskNotFoundError
from packages.observability.metrics import TASKS_CREATED
from apps.api.auth import Principal, require_api_auth
from packages.persistence.sqlalchemy import DocumentRecord
from packages.persistence.sqlalchemy import SqlAlchemyTaskRepository

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(require_api_auth)])


class CreateTaskRequest(BaseModel):
    goal: str = Field(min_length=5, max_length=10_000)
    document_id: UUID | None = None



class TaskDetailResponse(BaseModel):
    task_id: UUID
    goal: str
    status: TaskStatus
    version: int
    current_step_index: int
    error_message: str | None
    actions: list[dict]
    verification_result: dict | None

class TaskResponse(BaseModel):
    task_id: UUID
    goal: str
    status: TaskStatus
    version: int


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    limit: int = Query(default=50, ge=1, le=100),
    repository: SqlAlchemyTaskRepository = Depends(get_task_repository),
    principal: Principal = Depends(require_api_auth),
) -> list[TaskResponse]:
    tasks = repository.list_tasks(limit=limit, owner_id=principal.user_id)
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
def create_task(
    request: CreateTaskRequest,
    repository: SqlAlchemyTaskRepository = Depends(get_task_repository),
    principal: Principal = Depends(require_api_auth),
) -> TaskResponse:
    goal = request.goal
    if request.document_id is not None:
        row = repository.session.query(DocumentRecord).filter(
            DocumentRecord.document_id == str(request.document_id),
            DocumentRecord.user_id == str(principal.user_id),
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        context = row.extracted_text.strip()[:100_000]
        if context:
            goal = f"{goal}\n\n[ATTACHED DOCUMENT: {row.filename}]\n{context}"
        else:
            goal = f"{goal}\n\n[ATTACHED DOCUMENT: {row.filename}; text extraction unavailable]"
    task = Task(task_id=uuid4(), goal=goal)
    repository.create(task, owner_id=principal.user_id)
    TASKS_CREATED.inc()
    repository.append_audit(
        AuditEvent(
            task_id=task.task_id,
            event_type="TASK_CREATED",
            actor="API",
            details={"goal_length": len(task.goal)},
        )
    )
    # Commit before returning 201. FastAPI dependency teardown happens after
    # the response is created, so a dependency-only commit can report false success.
    try:
        repository.session.commit()
    except SQLAlchemyError as exc:
        repository.session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task could not be persisted.",
        ) from exc

    # Redis is a low-latency hint; SQL remains authoritative.
    broker = get_task_broker()
    if broker is not None:
        try:
            broker.publish(task.task_id)
        except Exception:
            pass

    return TaskResponse(
        task_id=task.task_id,
        goal=task.goal,
        status=task.status,
        version=task.version,
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    repository: SqlAlchemyTaskRepository = Depends(get_task_repository),
    principal: Principal = Depends(require_api_auth),
) -> TaskResponse:
    try:
        task = repository.get_owned(task_id, principal.user_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found.") from exc
    return TaskResponse(
        task_id=task.task_id,
        goal=task.goal,
        status=task.status,
        version=task.version,
    )

@router.get("/{task_id}/detail", response_model=TaskDetailResponse)
def get_task_detail(
    task_id: UUID,
    repository: SqlAlchemyTaskRepository = Depends(get_task_repository),
    principal: Principal = Depends(require_api_auth),
) -> TaskDetailResponse:
    try:
        task = repository.get_owned(task_id, principal.user_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found.") from exc

    return TaskDetailResponse(
        task_id=task.task_id,
        goal=task.goal,
        status=task.status,
        version=task.version,
        current_step_index=task.current_step_index,
        error_message=task.error_message,
        actions=[action.model_dump(mode="json") for action in task.actions],
        verification_result=(
            task.verification_result.model_dump(mode="json")
            if task.verification_result
            else None
        ),
    )
