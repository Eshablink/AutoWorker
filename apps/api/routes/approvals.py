from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from packages.domain.models import ActionStatus, ApprovalStatus, AuditEvent, TaskStatus
from packages.domain.repository import TaskNotFoundError
from packages.domain.state import TaskStateMachine
from packages.persistence.sqlalchemy import SqlAlchemyTaskRepository
from apps.api.database import get_task_repository

router = APIRouter(prefix="/approvals", tags=["approvals"])



class PendingApprovalResponse(BaseModel):
    approval_id: UUID
    task_id: UUID
    action_id: UUID
    goal: str
    requested_action_name: str
    tool_id: str
    payload_summary: dict
    risk_level: str
    reason_required: str
    status: ApprovalStatus
    created_at: datetime
    expires_at: datetime | None
    expired: bool

class ApprovalDecision(BaseModel):
    status: ApprovalStatus
    comment: str | None = None
    approver_id: str | None = None



@router.get("")
def list_pending_approvals(
    limit: int = Query(default=50, ge=1, le=100),
    repository: SqlAlchemyTaskRepository = Depends(get_task_repository),
) -> list[PendingApprovalResponse]:
    results: list[PendingApprovalResponse] = []
    for task in repository.list_pending_approvals(limit=limit):
        for action in task.actions:
            approval = action.approval_request
            if approval is None or approval.status != ApprovalStatus.PENDING:
                continue
            results.append(
                PendingApprovalResponse(
                    approval_id=approval.approval_id,
                    task_id=task.task_id,
                    action_id=action.action_id,
                    goal=task.goal,
                    requested_action_name=approval.requested_action_name,
                    tool_id=approval.tool_id,
                    payload_summary=approval.payload_summary,
                    risk_level=approval.risk_level.value,
                    reason_required=approval.reason_required,
                    status=approval.status,
                    created_at=approval.created_at,
                    expires_at=approval.expires_at,
                    expired=approval.expired,
                )
            )
            if len(results) >= limit:
                return results
    return results

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

    if approval.expired:
        previous_version = task.version
        approval.status = ApprovalStatus.EXPIRED
        approval.decided_at = datetime.now(timezone.utc)
        task.error_message = "Human approval request expired before a decision was recorded."
        _, state_audit = TaskStateMachine.transition(
            task,
            TaskStatus.FAILED,
            actor="APPROVAL_SERVICE",
            reason=task.error_message,
        )
        repository.save(task, audit_event=state_audit, expected_version=previous_version)
        action.status = ActionStatus.FAILED
        repository.append_audit(
            AuditEvent(
                task_id=task.task_id,
                action_id=action.action_id,
                event_type="APPROVAL_EXPIRED",
                actor="APPROVAL_SERVICE",
                details={"approval_id": str(approval_id)},
            )
        )
        return JSONResponse(status_code=409, content={"detail": "Approval request has expired."})

    previous_version = task.version
    approval.status = decision.status
    approval.approver_id = decision.approver_id
    approval.approval_comment = decision.comment
    approval.decided_at = datetime.now(timezone.utc)

    if decision.status == ApprovalStatus.APPROVED:
        action.status = ActionStatus.APPROVED
        _, state_audit = TaskStateMachine.transition(
            task,
            TaskStatus.RUNNING,
            actor="HUMAN_APPROVER",
            reason="Human approval granted.",
        )
    else:
        action.status = ActionStatus.REJECTED
        _, state_audit = TaskStateMachine.transition(
            task,
            TaskStatus.CANCELLED,
            actor="HUMAN_APPROVER",
            reason=decision.comment or "Human approval rejected.",
        )

    repository.save(task, audit_event=state_audit, expected_version=previous_version)
    repository.append_audit(
        AuditEvent(
            task_id=task.task_id,
            action_id=action.action_id,
            event_type="APPROVAL_DECIDED",
            actor="HUMAN_APPROVER",
            details={
                "approval_id": str(approval_id),
                "status": decision.status.value,
                "approver_id": decision.approver_id,
            },
        )
    )
    return {
        "approval_id": str(approval_id),
        "task_id": str(task.task_id),
        "status": decision.status,
        "task_status": task.status,
    }
