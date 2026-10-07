import pytest
from uuid import uuid4

from packages.domain.models import (
    ApprovalRequest,
    ApprovalStatus,
    PolicyDecision,
    PolicyOutcome,
    Task,
    TaskAction,
    TaskStatus,
    ToolRisk,
    VerificationResult,
)
from packages.domain.state import (
    InvariantViolationError,
    InvalidStateTransitionError,
    TaskStateMachine,
)


@pytest.fixture
def sample_task():
    return Task(goal="Execute refund for customer order after verifying policy.")


@pytest.fixture
def sample_verification(sample_task):
    return VerificationResult(
        task_id=sample_task.task_id,
        success=True,
        verification_type="db_query",
        query_or_check="SELECT * FROM refunds WHERE id = 'ref_101'",
        expected_state={"status": "PROCESSED"},
        actual_state={"status": "PROCESSED"},
        confidence_score=1.0,
    )


def test_valid_task_lifecycle(sample_task, sample_verification):
    actor = "WORKER_ENGINE"
    task, _ = TaskStateMachine.transition(sample_task, TaskStatus.PLANNING, actor)
    task, _ = TaskStateMachine.transition(task, TaskStatus.READY, actor)
    task, _ = TaskStateMachine.transition(task, TaskStatus.RUNNING, actor)
    task, _ = TaskStateMachine.transition(task, TaskStatus.VERIFYING, actor)
    task, _ = TaskStateMachine.record_verification(task, sample_verification)
    task, _ = TaskStateMachine.transition(task, TaskStatus.COMPLETED, actor)
    assert task.status == TaskStatus.COMPLETED
    assert task.verification_result.success is True


def test_illegal_state_transition_raises_error(sample_task):
    with pytest.raises(InvalidStateTransitionError):
        TaskStateMachine.transition(sample_task, TaskStatus.COMPLETED, "WORKER")


def test_terminal_state_lockout(sample_task):
    task, _ = TaskStateMachine.transition(sample_task, TaskStatus.CANCELLED, "USER")
    with pytest.raises(InvariantViolationError, match="is in terminal state"):
        TaskStateMachine.transition(task, TaskStatus.RUNNING, "WORKER")


def test_completion_rejected_if_verification_task_id_mismatches(sample_task):
    verification = VerificationResult(
        task_id=uuid4(),
        success=True,
        verification_type="db_query",
        query_or_check="SELECT 1",
        expected_state={},
        actual_state={},
        confidence_score=1.0,
    )
    with pytest.raises(InvariantViolationError, match="does not match Task task_id"):
        TaskStateMachine.record_verification(sample_task, verification)


def test_running_transition_fails_if_index_out_of_bounds(sample_task):
    task, _ = TaskStateMachine.transition(sample_task, TaskStatus.PLANNING, "SYSTEM")
    task, _ = TaskStateMachine.transition(task, TaskStatus.READY, "SYSTEM")
    task.current_step_index = 5
    with pytest.raises(InvariantViolationError, match="out of bounds"):
        TaskStateMachine.transition(task, TaskStatus.RUNNING, "WORKER")


def test_side_effecting_action_requires_idempotency_key(sample_task):
    action = TaskAction(
        task_id=sample_task.task_id,
        step_number=1,
        tool_id="execute_refund",
        is_side_effecting=True,
        idempotency_key=None,
        decision_summary="Execute refund in Stripe",
    )
    sample_task.actions = [action]
    task, _ = TaskStateMachine.transition(sample_task, TaskStatus.PLANNING, "SYSTEM")
    task, _ = TaskStateMachine.transition(task, TaskStatus.READY, "SYSTEM")
    with pytest.raises(InvariantViolationError, match="requires a non-empty idempotency_key"):
        TaskStateMachine.transition(task, TaskStatus.RUNNING, "WORKER")


def _high_risk_action(task, *, policy_task_id=None, policy_action_id=None, policy_tool_id=None):
    action = TaskAction(
        task_id=task.task_id,
        step_number=1,
        tool_id="execute_refund",
        is_side_effecting=True,
        idempotency_key="idempotency_key_101",
        decision_summary="Execute payment refund",
    )
    policy = PolicyDecision(
        task_id=policy_task_id or task.task_id,
        action_id=policy_action_id or action.action_id,
        tool_id=policy_tool_id or action.tool_id,
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        risk_level=ToolRisk.HIGH,
        reason="Refund requires approval",
    )
    action.policy_decision = policy
    return action, policy


def _ready(task):
    task, _ = TaskStateMachine.transition(task, TaskStatus.PLANNING, "SYSTEM")
    task, _ = TaskStateMachine.transition(task, TaskStatus.READY, "SYSTEM")
    return task


def test_approval_binding_action_mismatch_rejected(sample_task):
    action, policy = _high_risk_action(sample_task)
    action.approval_request = ApprovalRequest(
        task_id=sample_task.task_id,
        action_id=uuid4(),
        policy_decision_id=policy.decision_id,
        status=ApprovalStatus.APPROVED,
        requested_action_name="Execute Refund",
        tool_id="execute_refund",
        payload_summary={"amount": 1000},
        risk_level=ToolRisk.HIGH,
        reason_required="High value transaction",
        approver_id="supervisor_01",
    )
    sample_task.actions = [action]
    task = _ready(sample_task)
    with pytest.raises(InvariantViolationError, match="does not match TaskAction ID"):
        TaskStateMachine.transition(task, TaskStatus.RUNNING, "WORKER")


def test_policy_task_binding_mismatch_rejected(sample_task):
    action, _ = _high_risk_action(sample_task, policy_task_id=uuid4())
    sample_task.actions = [action]
    task = _ready(sample_task)
    with pytest.raises(InvariantViolationError, match="PolicyDecision task_id"):
        TaskStateMachine.transition(task, TaskStatus.RUNNING, "WORKER")


def test_policy_action_binding_mismatch_rejected(sample_task):
    action, _ = _high_risk_action(sample_task, policy_action_id=uuid4())
    sample_task.actions = [action]
    task = _ready(sample_task)
    with pytest.raises(InvariantViolationError, match="PolicyDecision action_id"):
        TaskStateMachine.transition(task, TaskStatus.RUNNING, "WORKER")


def test_policy_tool_binding_mismatch_rejected(sample_task):
    action, _ = _high_risk_action(sample_task, policy_tool_id="different_tool")
    sample_task.actions = [action]
    task = _ready(sample_task)
    with pytest.raises(InvariantViolationError, match="PolicyDecision tool_id"):
        TaskStateMachine.transition(task, TaskStatus.RUNNING, "WORKER")


def test_running_transition_rejects_action_from_another_task(sample_task):
    other_task = Task(goal="Another task")
    action = TaskAction(
        task_id=other_task.task_id,
        step_number=1,
        tool_id="browser_click",
        decision_summary="Click button",
    )
    sample_task.actions = [action]
    task = _ready(sample_task)
    with pytest.raises(InvariantViolationError, match="TaskAction task_id"):
        TaskStateMachine.transition(task, TaskStatus.RUNNING, "WORKER")


def test_running_transition_rejects_denied_policy(sample_task):
    action = TaskAction(
        task_id=sample_task.task_id,
        step_number=1,
        tool_id="execute_refund",
        idempotency_key="refund-1",
        is_side_effecting=True,
        decision_summary="Execute refund",
        policy_decision=PolicyDecision(
            task_id=sample_task.task_id,
            action_id=uuid4(),
            tool_id="execute_refund",
            outcome=PolicyOutcome.DENY,
            risk_level=ToolRisk.LOW,
            reason="Refund is blocked by policy.",
        ),
    )
    action.policy_decision = action.policy_decision.model_copy(update={"action_id": action.action_id})
    sample_task.actions = [action]
    task = _ready(sample_task)
    with pytest.raises(InvariantViolationError, match="denied execution"):
        TaskStateMachine.transition(task, TaskStatus.RUNNING, "WORKER")


def test_running_transition_rejects_action_without_policy_decision(sample_task):
    action = TaskAction(
        task_id=sample_task.task_id,
        step_number=1,
        tool_id="browser_click",
        decision_summary="Click button",
    )
    sample_task.actions = [action]
    task = _ready(sample_task)
    with pytest.raises(InvariantViolationError, match="without a PolicyDecision"):
        TaskStateMachine.transition(task, TaskStatus.RUNNING, "WORKER")


def test_expired_approval_cannot_resume_task(sample_task):
    from datetime import datetime, timedelta, timezone

    action, policy = _high_risk_action(sample_task)
    action.approval_request = ApprovalRequest(
        task_id=sample_task.task_id,
        action_id=action.action_id,
        policy_decision_id=policy.decision_id,
        status=ApprovalStatus.APPROVED,
        requested_action_name="Execute Refund",
        tool_id="execute_refund",
        payload_summary={"amount": 1000},
        risk_level=ToolRisk.HIGH,
        reason_required="High value transaction",
        approver_id="manager",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    sample_task.actions = [action]
    task = _ready(sample_task)
    with pytest.raises(InvariantViolationError, match="has expired"):
        TaskStateMachine.transition(task, TaskStatus.RUNNING, "WORKER")
