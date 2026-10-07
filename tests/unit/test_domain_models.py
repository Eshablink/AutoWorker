import pytest
from uuid import uuid4
from pydantic import ValidationError

from packages.domain.models import (
    AuditEvent,
    EvidenceReference,
    PolicyDecision,
    PolicyOutcome,
    Task,
    TaskAction,
    TaskStatus,
    ToolDefinition,
    ToolRisk,
)


def test_task_creation_defaults():
    task = Task(goal="Process invoice and verify entry in ERP database.")
    assert task.status == TaskStatus.CREATED
    assert task.version == 1
    assert task.current_step_index == 0
    assert task.actions == []
    assert task.context_memory == {}


def test_blank_goal_raises_validation_error():
    with pytest.raises(ValidationError):
        Task(goal="   ")


def test_task_action_uses_auditable_summary_not_private_thought():
    action = TaskAction(
        task_id=uuid4(),
        step_number=1,
        tool_id="browser_click",
        decision_summary="Click email attachment link to access PDF invoice.",
        reason_code="DOCUMENT_OPEN",
    )
    assert action.decision_summary
    assert not hasattr(action, "thought_rationale")


def test_action_retry_count_exceeding_max_raises_error():
    with pytest.raises(ValidationError, match="retry_count"):
        TaskAction(
            task_id=uuid4(),
            step_number=1,
            tool_id="browser_click",
            decision_summary="Retry submission",
            retry_count=4,
            max_retries=3,
        )


def test_high_risk_policy_outcome_allow_is_forbidden():
    with pytest.raises(ValidationError, match="High-risk tool calls"):
        PolicyDecision(
            task_id=uuid4(),
            action_id=uuid4(),
            tool_id="execute_payment_refund",
            outcome=PolicyOutcome.ALLOW,
            risk_level=ToolRisk.HIGH,
            reason="Illegal bypass attempt",
        )


def test_tool_definition_timeout_bounds():
    with pytest.raises(ValidationError):
        ToolDefinition(
            tool_id="test_tool",
            name="Test",
            description="Desc",
            input_schema={},
            output_schema={},
            timeout_seconds=0,
        )


def test_evidence_reference_non_empty_validation():
    with pytest.raises(ValidationError, match="cannot be empty"):
        EvidenceReference(
            task_id=uuid4(),
            kind="   ",
            uri_or_path="s3://evidence/shot.png",
        )


def test_audit_event_immutability():
    event = AuditEvent(
        task_id=uuid4(),
        event_type="STATE_TRANSITION",
        actor="WORKER",
        details={"status": "RUNNING"},
    )
    with pytest.raises(ValidationError):
        event.actor = "HACKER"


def test_short_non_whitespace_goal_is_rejected():
    with pytest.raises(ValidationError, match="at least 5 non-whitespace characters"):
        Task(goal="    a")


def test_whitespace_idempotency_key_is_rejected():
    with pytest.raises(ValidationError, match="idempotency_key"):
        TaskAction(
            task_id=uuid4(),
            step_number=1,
            tool_id="browser_click",
            decision_summary="Click button",
            idempotency_key="   ",
        )


def test_policy_version_cannot_be_blank():
    with pytest.raises(ValidationError, match="policy_version"):
        PolicyDecision(
            task_id=uuid4(),
            action_id=uuid4(),
            tool_id="test_tool",
            outcome=PolicyOutcome.ALLOW,
            risk_level=ToolRisk.LOW,
            reason="Allowed for testing",
            policy_version="   ",
        )


def test_approval_request_expired_property():
    from datetime import datetime, timedelta, timezone
    from packages.domain.models import ApprovalRequest, ApprovalStatus

    approval = ApprovalRequest(
        task_id=uuid4(),
        action_id=uuid4(),
        policy_decision_id=uuid4(),
        status=ApprovalStatus.PENDING,
        requested_action_name="Approve invoice",
        tool_id="erp_submit",
        payload_summary={},
        risk_level=ToolRisk.HIGH,
        reason_required="Financial write",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    assert approval.expired is True
