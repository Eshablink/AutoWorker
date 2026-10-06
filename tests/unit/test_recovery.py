import pytest

from packages.domain.models import ActionStatus, Task, TaskAction, TaskStatus
from packages.worker.recovery import RecoveryCoordinator


def make_task(side_effecting=False):
    task = Task(goal="Process an invoice", status=TaskStatus.RUNNING)
    task.actions = [
        TaskAction(
            task_id=task.task_id,
            step_number=1,
            tool_id="invoice_tool",
            decision_summary="Process invoice",
            status=ActionStatus.RUNNING,
            is_side_effecting=side_effecting,
            idempotency_key="idempotent-1" if side_effecting else None,
        )
    ]
    return task


def test_running_action_is_requeued_for_recovery():
    task = make_task()
    recovered = RecoveryCoordinator().recover(task)
    assert recovered.status == TaskStatus.RECOVERING
    assert recovered.actions[0].status == ActionStatus.PENDING
    assert recovered.actions[0].retry_count == 1


def test_side_effect_without_idempotency_fails_recovery():
    task = make_task(side_effecting=True)
    task.actions[0].idempotency_key = None
    recovered = RecoveryCoordinator().recover(task)
    assert recovered.status == TaskStatus.FAILED
    assert recovered.error_message


def test_non_running_task_is_not_recovered():
    task = Task(goal="Process an invoice")
    with pytest.raises(ValueError):
        RecoveryCoordinator().recover(task)
