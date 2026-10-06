"""Recovery coordinator for interrupted worker tasks."""

from packages.domain.models import ActionStatus, Task, TaskStatus


class RecoveryCoordinator:
    def recover(self, task: Task) -> Task:
        if task.status not in {TaskStatus.RUNNING, TaskStatus.RECOVERING}:
            raise ValueError(f"Task {task.task_id} is not recoverable from {task.status.value}.")

        if task.actions:
            action = task.actions[task.current_step_index]
            if action.status == ActionStatus.RUNNING:
                if action.is_side_effecting and not action.idempotency_key:
                    task.status = TaskStatus.FAILED
                    task.error_message = "Interrupted side-effecting action has no idempotency key."
                    return task
                action.status = ActionStatus.PENDING
                action.retry_count += 1
                if action.retry_count > action.max_retries:
                    action.status = ActionStatus.FAILED
                    task.status = TaskStatus.FAILED
                    task.error_message = "Action exceeded retry limit during recovery."
                    return task

        task.status = TaskStatus.RECOVERING
        return task
