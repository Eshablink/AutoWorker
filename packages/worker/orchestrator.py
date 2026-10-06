"""Task execution orchestration across policy, worker, and domain state."""

from packages.domain.models import ActionStatus, PolicyOutcome, Task, TaskStatus
from packages.domain.state import TaskStateMachine
from packages.policy.engine import PolicyEngine
from packages.tools.registry import ToolRegistry
from packages.worker.execution import ExecutionWorker, ToolExecutionResult


class TaskOrchestrator:
    def __init__(
        self,
        registry: ToolRegistry,
        policy_engine: PolicyEngine,
        worker: ExecutionWorker,
    ) -> None:
        self.registry = registry
        self.policy_engine = policy_engine
        self.worker = worker

    def prepare(self, task: Task) -> Task:
        """Evaluate the current action and move a ready task into execution."""
        if task.status != TaskStatus.READY:
            raise ValueError(f"Task {task.task_id} must be READY before execution.")

        if not task.actions:
            raise ValueError("Task has no actions to execute.")

        action = task.actions[task.current_step_index]
        decision = self.policy_engine.evaluate(task, action)
        action.policy_decision = decision

        if decision.outcome == PolicyOutcome.DENY:
            task.error_message = decision.reason
            TaskStateMachine.transition(task, TaskStatus.CANCELLED, actor="POLICY_ENGINE", reason=decision.reason)
            return task

        if decision.outcome == PolicyOutcome.REQUIRE_APPROVAL:
            task.status = TaskStatus.WAITING_APPROVAL
            action.status = ActionStatus.WAITING_APPROVAL
            task.version += 1
            return task

        TaskStateMachine.transition(task, TaskStatus.RUNNING, actor="ORCHESTRATOR")
        return task

    def execute_current(self, task: Task) -> ToolExecutionResult:
        if task.status != TaskStatus.RUNNING:
            raise ValueError(f"Task {task.task_id} must be RUNNING before execution.")

        action = task.actions[task.current_step_index]
        return self.worker.execute_action(action)
