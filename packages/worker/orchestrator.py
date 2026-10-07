"""Task execution orchestration across policy, worker, and domain state."""

from packages.audit.events import EventBus, EventType, TaskEvent
from packages.domain.models import ActionStatus, ApprovalRequest, PolicyOutcome, Task, TaskStatus
from packages.domain.state import TaskStateMachine
from packages.policy.engine import PolicyEngine
from packages.tools.registry import ToolRegistry
from packages.verification.engine import VerificationCheck, VerificationEngine
from packages.worker.execution import ExecutionWorker, ToolExecutionResult


class TaskOrchestrator:
    def __init__(
        self,
        registry: ToolRegistry,
        policy_engine: PolicyEngine,
        worker: ExecutionWorker,
        event_bus: EventBus | None = None,
        verification_engine: VerificationEngine | None = None,
    ) -> None:
        self.registry = registry
        self.policy_engine = policy_engine
        self.worker = worker
        self.event_bus = event_bus or EventBus()
        self.verification_engine = verification_engine or VerificationEngine()

    def prepare(self, task: Task) -> Task:
        """Evaluate the current action and move a ready task into execution."""
        if task.status != TaskStatus.READY:
            raise ValueError(f"Task {task.task_id} must be READY before execution.")
        if not task.actions:
            raise ValueError("Task has no actions to execute.")
        if not 0 <= task.current_step_index < len(task.actions):
            raise ValueError("Task current_step_index is out of bounds.")

        action = task.actions[task.current_step_index]
        decision = self.policy_engine.evaluate(task, action)
        action.policy_decision = decision

        if decision.outcome == PolicyOutcome.DENY:
            task.error_message = decision.reason
            TaskStateMachine.transition(
                task,
                TaskStatus.FAILED,
                actor="POLICY_ENGINE",
                reason=decision.reason,
            )
            action.status = ActionStatus.REJECTED
            self._publish_state(task, decision.reason)
            return task

        if decision.outcome == PolicyOutcome.REQUIRE_APPROVAL:
            TaskStateMachine.transition(
                task,
                TaskStatus.WAITING_APPROVAL,
                actor="POLICY_ENGINE",
                reason=decision.reason,
            )
            action.approval_request = ApprovalRequest(
                task_id=task.task_id,
                action_id=action.action_id,
                policy_decision_id=decision.decision_id,
                requested_action_name=action.decision_summary,
                tool_id=action.tool_id,
                payload_summary=action.tool_input,
                risk_level=decision.risk_level,
                reason_required=decision.reason,
            )
            action.status = ActionStatus.WAITING_APPROVAL
            self.event_bus.publish(
                TaskEvent(
                    task_id=task.task_id,
                    event_type=EventType.APPROVAL_REQUIRED,
                    payload={
                        "action_id": str(action.action_id),
                        "tool_id": action.tool_id,
                        "reason": decision.reason,
                    },
                )
            )
            self._publish_state(task, decision.reason)
            return task

        TaskStateMachine.transition(task, TaskStatus.RUNNING, actor="ORCHESTRATOR")
        self._publish_state(task, "Policy allowed execution.")
        return task

    def execute_current(self, task: Task) -> ToolExecutionResult:
        if task.status != TaskStatus.RUNNING:
            raise ValueError(f"Task {task.task_id} must be RUNNING before execution.")
        if not task.actions or not 0 <= task.current_step_index < len(task.actions):
            raise ValueError("Task current action is unavailable.")

        action = task.actions[task.current_step_index]
        if action.task_id != task.task_id:
            raise ValueError("Current action task_id does not match task task_id.")
        if action.status not in {ActionStatus.PENDING, ActionStatus.APPROVED}:
            raise ValueError(
                f"Current action cannot execute from status '{action.status.value}'."
            )

        self.event_bus.publish(
            TaskEvent(
                task_id=task.task_id,
                action_id=action.action_id,
                event_type=EventType.ACTION_STARTED,
                payload={"action_id": str(action.action_id), "tool_id": action.tool_id},
            )
        )
        try:
            result = self.worker.execute_action(action)
        except Exception as exc:
            action.error_message = str(exc)
            action.status = ActionStatus.FAILED
            self.event_bus.publish(
                TaskEvent(
                    task_id=task.task_id,
                    action_id=action.action_id,
                    event_type=EventType.ACTION_FAILED,
                    payload={"error": str(exc)},
                )
            )
            raise

        self.event_bus.publish(
            TaskEvent(
                task_id=task.task_id,
                action_id=action.action_id,
                event_type=EventType.ACTION_COMPLETED,
                payload={"action_id": str(action.action_id)},
            )
        )
        return result

    def verify_current(self, task: Task, checks: list[VerificationCheck]) -> Task:
        if task.status != TaskStatus.RUNNING:
            raise ValueError(f"Task {task.task_id} must be RUNNING before verification.")
        if not task.actions or not 0 <= task.current_step_index < len(task.actions):
            raise ValueError("Task current action is unavailable.")

        action = task.actions[task.current_step_index]
        if action.task_id != task.task_id:
            raise ValueError("Current action task_id does not match task task_id.")
        if action.status != ActionStatus.COMPLETED:
            raise ValueError(
                f"Current action must be COMPLETED before verification; got '{action.status.value}'."
            )

        TaskStateMachine.transition(
            task,
            TaskStatus.VERIFYING,
            actor="ORCHESTRATOR",
            reason="Action execution completed; starting verification.",
        )
        self.event_bus.publish(
            TaskEvent(
                task_id=task.task_id,
                action_id=action.action_id,
                event_type=EventType.VERIFICATION_STARTED,
                payload={"action_id": str(action.action_id)},
            )
        )
        result = self.verification_engine.verify(task.task_id, action, checks=checks)
        TaskStateMachine.record_verification(task, result, actor="VERIFICATION_ENGINE")
        self.event_bus.publish(
            TaskEvent(
                task_id=task.task_id,
                action_id=action.action_id,
                event_type=EventType.VERIFICATION_COMPLETED,
                payload={"success": result.success, "confidence": result.confidence_score},
            )
        )

        if result.success:
            TaskStateMachine.transition(
                task,
                TaskStatus.COMPLETED,
                actor="ORCHESTRATOR",
                reason="Verification passed.",
            )
        elif action.retry_count >= action.max_retries:
            task.error_message = (
                f"Verification failed and action {action.action_id} reached "
                f"the maximum retry count of {action.max_retries}."
            )
            TaskStateMachine.transition(
                task,
                TaskStatus.FAILED,
                actor="ORCHESTRATOR",
                reason=task.error_message,
            )
            action.status = ActionStatus.FAILED
            action.error_message = task.error_message
        else:
            TaskStateMachine.transition(
                task,
                TaskStatus.RECOVERING,
                actor="ORCHESTRATOR",
                reason="Verification failed; action requires recovery.",
            )
            action.status = ActionStatus.PENDING
            action.retry_count += 1
            action.error_message = None

        self._publish_state(task, "Verification lifecycle transition completed.")
        return task

    def _publish_state(self, task: Task, reason: str) -> None:
        self.event_bus.publish(
            TaskEvent(
                task_id=task.task_id,
                event_type=EventType.TASK_STATE_CHANGED,
                payload={"status": task.status.value, "version": task.version, "reason": reason},
            )
        )
