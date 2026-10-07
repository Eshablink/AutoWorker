from datetime import datetime, timedelta, timezone
from uuid import uuid4

from apps.api.routes.approvals import ApprovalDecision, decide_approval
from packages.domain.models import (
    ActionStatus,
    ApprovalRequest,
    ApprovalStatus,
    PolicyDecision,
    PolicyOutcome,
    Task,
    TaskAction,
    TaskStatus,
    ToolRisk,
)
from packages.persistence.memory import InMemoryTaskRepository


def waiting_task() -> tuple[Task, ApprovalRequest]:
    task = Task(goal="Process the approved invoice", status=TaskStatus.READY)
    action = TaskAction(
        task_id=task.task_id,
        step_number=1,
        tool_id="erp_submit",
        decision_summary="Submit invoice to ERP",
        status=ActionStatus.WAITING_APPROVAL,
        is_side_effecting=True,
        idempotency_key="invoice-101",
        policy_decision=PolicyDecision(
            task_id=task.task_id,
            action_id=uuid4(),
            tool_id="erp_submit",
            outcome=PolicyOutcome.REQUIRE_APPROVAL,
            risk_level=ToolRisk.HIGH,
            reason="ERP financial write requires approval",
        ),
    )
    action.action_id = action.policy_decision.action_id
    approval = ApprovalRequest(
        task_id=task.task_id,
        action_id=action.action_id,
        policy_decision_id=action.policy_decision.decision_id,
        requested_action_name="Submit invoice",
        tool_id="erp_submit",
        payload_summary={"invoice": "INV-101"},
        risk_level=ToolRisk.HIGH,
        reason_required="Financial side effect",
    )
    action.approval_request = approval
    task.actions = [action]
    task.status = TaskStatus.WAITING_APPROVAL
    return task, approval


def test_approved_request_resumes_task():
    repo = InMemoryTaskRepository()
    task, approval = waiting_task()
    repo.create(task)

    result = decide_approval(
        approval.approval_id,
        ApprovalDecision(status=ApprovalStatus.APPROVED, approver_id="manager"),
        repo,
    )

    updated = repo.get(task.task_id)
    assert result["task_status"] == TaskStatus.RUNNING
    assert updated.actions[0].approval_request.status == ApprovalStatus.APPROVED
    assert updated.actions[0].status == ActionStatus.APPROVED


def test_rejected_request_cancels_task():
    repo = InMemoryTaskRepository()
    task, approval = waiting_task()
    repo.create(task)

    decide_approval(
        approval.approval_id,
        ApprovalDecision(
            status=ApprovalStatus.REJECTED,
            approver_id="manager",
            comment="Reject for review",
        ),
        repo,
    )

    updated = repo.get(task.task_id)
    assert updated.status == TaskStatus.CANCELLED
    assert updated.actions[0].status == ActionStatus.REJECTED
    assert len(repo.list_audit(task.task_id)) == 2


def test_expired_approval_is_failed_and_not_accepted():
    repo = InMemoryTaskRepository()
    task, approval = waiting_task()
    approval.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    repo.create(task)

    import pytest

    with pytest.raises(Exception, match="expired"):
        decide_approval(
            approval.approval_id,
            ApprovalDecision(status=ApprovalStatus.APPROVED, approver_id="manager"),
            repo,
        )

    updated = repo.get(task.task_id)
    assert updated.status == TaskStatus.FAILED
    assert updated.actions[0].approval_request.status == ApprovalStatus.EXPIRED
    assert repo.list_audit(task.task_id)[-1].event_type == "APPROVAL_EXPIRED"
