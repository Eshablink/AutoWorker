from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from packages.audit.events import EventBus, EventType, TaskEvent
from packages.domain.models import ApprovalStatus, TaskStatus
from packages.domain.repository import TaskNotFoundError
from packages.domain.state import TaskStateMachine
from packages.persistence.sqlalchemy import SqlAlchemyTaskRepository
from apps.api.database import get_task_repository

router = APIRouter(prefix="/approvals", tags=["approvals"])
event_bus = EventBus()


class ApprovalDecision(BaseModel):
    status: ApprovalStatus
    comment: str | None = None
    approver_id: str | None = None


@router.post("/{approval_id}")
def decide_approval(
    approval_id: UUID,
    decision: ApprovalDecision,
    repository: SqlAlchemyTaskRepository = Depends(get_task_repository),
):
    if decision.status not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
        raise HTTPException(status_code=400, detail="Approval must be APPROVED or REJECTED.")

    try:
        task = repository.find_by_approval_id(approval_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Approval request not found.") from exc

    if task.status != TaskStatus.WAITING_APPROVAL:
        raise HTTPException(status_code=409, detail="Task is not waiting for approval.")

    action = next(
        (
            item
            for item in task.actions
            if item.approval_request and item.approval_request.approval_id == approval_id
        ),
        None,
    )
    if action is None or action.approval_request is None:
        raise HTTPException(status_code=404, detail="Approval request not found.")

    approval = action.approval_request
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=409, detail="Approval request has already been decided.")

    previous_version = task.version
    approval.status = decision.status
    approval.approver_id = decision.approver_id
    approval.approval_comment = decision.comment
    approval.decided_at = datetime.now(timezone.utc)

    if decision.status == ApprovalStatus.APPROVED:
        action.status = __import__("packages.domain.models", fromlist=["ActionStatus"]).ActionStatus.APPROVED
        TaskStateMachine.transition(
            task,
            TaskStatus.RUNNING,
            actor="HUMAN_APPROVER",
            reason="Human approval granted.",
        )
    else:
        action.status = __import__("packages.domain.models", fromlist=["ActionStatus"]).ActionStatus.REJECTED
        TaskStateMachine.transition(
            task,
            TaskStatus.CANCELLED,
            actor="HUMAN_APPROVER",
            reason=decision.comment or "Human approval rejected.",
        )

    _, audit = TaskStateMachine.transition if False else (task, None)
    repository.save(task, audit_event=__import__("packages.domain.models", fromlist=["AuditEvent"]).AuditEvent(
        task_id=task.task_id,
        action_id=action.action_id,
        event_type="APPROVAL_DECIDED",
        actor="HUMAN_APPROVER",
        details={"approval_id": str(approval_id), "status": decision.status.value, "approver_id": decision.approver_id},
    ), expected_version=previous_version)

    event_bus.publish(TaskEvent(
        task_id=task.task_id,
        action_id=action.action_id,
        event_type=EventType.APPROVAL_DECIDED,
        payload={"approval_id": str(approval_id), "status": decision.status.value},
    ))
    return {"approval_id": str(approval_id), "task_id": str(task.task_id), "status": decision.status, "task_status": task.status}
