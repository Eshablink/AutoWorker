"""Crash-safe task recovery coordination for interrupted actions."""

from packages.domain.models import ActionStatus, Task, TaskStatus
from packages.domain.state import TaskStateMachine


class RecoveryCoordinator:
    """Requeue interrupted work while preventing unsafe side-effect retries."""

    def __init__(self, max_retries: int = 3) -> None:
        if max_retries < 1:
            raise ValueError("max_retries must be at least 1")
        self.max_retries = max_retries

    def recover(self, task: Task) -> Task:
        if task.status != TaskStatus.RUNNING:
            raise ValueError(f"Task {task.task_id} must be RUNNING before recovery.")

        if not task.actions:
            raise ValueError(f"Task {task.task_id} has no action to recover.")

        if not 0 <= task.current_step_index < len(task.actions):
            raise ValueError(f"Task {task.task_id} current_step_index is out of bounds.")

        action = task.actions[task.current_step_index]
        if action.status != ActionStatus.RUNNING:
            raise ValueError(
                f"Task {task.task_id} current action must be RUNNING before recovery."
            )

        if action.is_side_effecting and not (
            action.idempotency_key and action.idempotency_key.strip()
        ):
            task.error_message = (
                f"Action {action.action_id} is side-effecting and cannot be safely retried "
                "without an idempotency key."
            )
            TaskStateMachine.transition(
                task,
                TaskStatus.FAILED,
                actor="RECOVERY_COORDINATOR",
                reason=task.error_message,
            )
            action.status = ActionStatus.FAILED
            action.error_message = task.error_message
            return task

        if action.retry_count >= self.max_retries:
            task.error_message = (
                f"Action {action.action_id} exceeded the maximum retry count "
                f"of {self.max_retries}."
            )
            TaskStateMachine.transition(
                task,
                TaskStatus.FAILED,
                actor="RECOVERY_COORDINATOR",
                reason=task.error_message,
            )
            action.status = ActionStatus.FAILED
            action.error_message = task.error_message
            return task

        TaskStateMachine.transition(
            task,
            TaskStatus.RECOVERING,
            actor="RECOVERY_COORDINATOR",
            reason="Requeue interrupted action after worker recovery.",
        )
        action.status = ActionStatus.PENDING
        action.retry_count += 1
        action.error_message = None
        return task
