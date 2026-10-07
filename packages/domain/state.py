"""AutoWorker task state machine, safety invariants, and lifecycle rules."""

from datetime import datetime, timezone
from typing import Dict, Optional, Set, Tuple

from packages.domain.models import (
    ActionStatus,
    ApprovalStatus,
    AuditEvent,
    PolicyOutcome,
    Task,
    TaskStatus,
    ToolRisk,
    VerificationResult,
)


class InvalidStateTransitionError(Exception):
    """Raised when a requested lifecycle transition is not allowed."""


class InvariantViolationError(Exception):
    """Raised when a domain safety invariant is breached."""


VALID_TASK_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.CREATED: {TaskStatus.PLANNING, TaskStatus.CANCELLED},
    TaskStatus.PLANNING: {TaskStatus.READY, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.READY: {TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL, TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.RUNNING: {
        TaskStatus.WAITING_APPROVAL,
        TaskStatus.RECOVERING,
        TaskStatus.VERIFYING,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.WAITING_APPROVAL: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.RECOVERING: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.VERIFYING: {
        TaskStatus.COMPLETED,
        TaskStatus.RECOVERING,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


class TaskStateMachine:
    """Enforces lifecycle transitions and execution safety invariants."""

    @staticmethod
    def transition(
        task: Task,
        target_status: TaskStatus,
        actor: str,
        reason: Optional[str] = None,
    ) -> Tuple[Task, AuditEvent]:
        current_status = task.status

        if current_status == target_status:
            return task, AuditEvent(
                task_id=task.task_id,
                event_type="STATE_TRANSITION_NOOP",
                actor=actor,
                details={"status": current_status.value, "version": task.version, "reason": "Already in target state"},
            )

        if current_status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
            raise InvariantViolationError(
                f"Task {task.task_id} is in terminal state '{current_status.value}' and cannot be modified."
            )

        allowed_targets = VALID_TASK_TRANSITIONS.get(current_status, set())
        if target_status not in allowed_targets:
            raise InvalidStateTransitionError(
                f"Cannot transition task {task.task_id} from '{current_status.value}' "
                f"to '{target_status.value}'. Allowed transitions: {[s.value for s in allowed_targets]}"
            )

        TaskStateMachine.validate_invariants(task, target_status)
        task.status = target_status
        task.version += 1
        task.updated_at = datetime.now(timezone.utc)

        return task, AuditEvent(
            task_id=task.task_id,
            event_type="STATE_TRANSITION",
            actor=actor,
            details={
                "from_status": current_status.value,
                "to_status": target_status.value,
                "version": task.version,
                "reason": reason or "Normal lifecycle transition",
            },
        )

    @staticmethod
    def validate_invariants(task: Task, target_status: TaskStatus) -> None:
        if task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
            raise InvariantViolationError(
                f"Task {task.task_id} is in terminal state '{task.status.value}' and cannot be modified."
            )

        if target_status == TaskStatus.COMPLETED:
            verification = task.verification_result
            if verification is None or verification.task_id != task.task_id:
                raise InvariantViolationError("Task cannot complete without a matching VerificationResult.")
            if not verification.success:
                raise InvariantViolationError("Task cannot complete because verification failed.")

        if target_status != TaskStatus.RUNNING:
            return

        if task.actions and not 0 <= task.current_step_index < len(task.actions):
            raise InvariantViolationError("Task current_step_index is out of bounds.")
        if not task.actions and task.current_step_index != 0:
            raise InvariantViolationError(
                f"Task {task.task_id} current_step_index ({task.current_step_index}) is out of bounds."
            )
        if not task.actions:
            return

        action = task.actions[task.current_step_index]
        if action.task_id != task.task_id:
            raise InvariantViolationError(
                f"TaskAction task_id '{action.task_id}' does not match Task ID '{task.task_id}'."
            )
        if action.status not in {ActionStatus.PENDING, ActionStatus.APPROVED}:
            raise InvariantViolationError(
                f"Current TaskAction status '{action.status.value}' cannot execute."
            )
        policy = action.policy_decision
        if policy is None:
            raise InvariantViolationError(
                f"Action {action.action_id} cannot enter RUNNING without a PolicyDecision."
            )
        requires_idempotency = action.is_side_effecting or (
            policy is not None and policy.risk_level in {ToolRisk.HIGH, ToolRisk.CRITICAL}
        )
        if requires_idempotency and not (action.idempotency_key and action.idempotency_key.strip()):
            raise InvariantViolationError(
                f"Action {action.action_id} is side-effecting/high-risk and requires a non-empty idempotency_key."
            )
        if policy.outcome == PolicyOutcome.DENY:
            raise InvariantViolationError(
                f"PolicyDecision denied execution: {policy.reason}"
            )
        if policy.task_id != task.task_id:
            raise InvariantViolationError(
                f"PolicyDecision task_id '{policy.task_id}' does not match Task ID '{task.task_id}'."
            )
        if policy.action_id != action.action_id:
            raise InvariantViolationError(
                f"PolicyDecision action_id '{policy.action_id}' does not match TaskAction ID '{action.action_id}'."
            )
        if policy.tool_id != action.tool_id:
            raise InvariantViolationError(
                f"PolicyDecision tool_id '{policy.tool_id}' does not match TaskAction tool_id '{action.tool_id}'."
            )
        requires_approval = policy.outcome == PolicyOutcome.REQUIRE_APPROVAL or policy.risk_level in {
            ToolRisk.HIGH,
            ToolRisk.CRITICAL,
        }
        if not requires_approval:
            return
        approval = action.approval_request
        if approval is None:
            raise InvariantViolationError(
                f"Action {action.action_id} requires explicit human approval before execution."
            )
        if approval.task_id != task.task_id:
            raise InvariantViolationError(
                f"ApprovalRequest task_id '{approval.task_id}' does not match Task ID '{task.task_id}'."
            )
        if approval.action_id != action.action_id:
            raise InvariantViolationError(
                f"ApprovalRequest action_id '{approval.action_id}' does not match TaskAction ID '{action.action_id}'."
            )
        if approval.policy_decision_id != policy.decision_id:
            raise InvariantViolationError(
                f"ApprovalRequest policy_decision_id '{approval.policy_decision_id}' does not match PolicyDecision ID '{policy.decision_id}'."
            )
        if approval.status != ApprovalStatus.APPROVED:
            raise InvariantViolationError(
                f"Action {action.action_id} approval request status is '{approval.status.value}', expected 'APPROVED'."
            )

    @staticmethod
    def record_verification(
        task: Task,
        verification_result: VerificationResult,
        actor: str = "VERIFICATION_ENGINE",
    ) -> Tuple[Task, AuditEvent]:
        if verification_result.task_id != task.task_id:
            raise InvariantViolationError(
                f"VerificationResult task_id '{verification_result.task_id}' does not match "
                f"Task task_id '{task.task_id}'."
            )
        task.verification_result = verification_result
        task.version += 1
        task.updated_at = datetime.now(timezone.utc)
        return task, AuditEvent(
            task_id=task.task_id,
            action_id=verification_result.action_id,
            event_type="VERIFICATION_RECORDED",
            actor=actor,
            details={
                "verification_id": str(verification_result.verification_id),
                "success": verification_result.success,
                "verification_type": verification_result.verification_type,
                "confidence_score": verification_result.confidence_score,
                "version": task.version,
            },
        )
