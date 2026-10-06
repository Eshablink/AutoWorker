import pytest

from packages.domain.models import ActionStatus, TaskAction
from packages.worker.execution import ExecutionWorker, ToolExecutionResult


class FakeExecutor:
    def execute(self, action):
        return ToolExecutionResult(
            output={"ok": True, "tool": action.tool_id},
            observation="Tool completed successfully.",
        )


def make_action(status=ActionStatus.PENDING):
    return TaskAction(
        task_id=__import__("uuid").uuid4(),
        step_number=1,
        tool_id="browser_click",
        decision_summary="Execute browser click.",
        status=status,
    )


def test_worker_executes_pending_action():
    action = make_action()
    result = ExecutionWorker(FakeExecutor()).execute_action(action)
    assert result.output["ok"] is True
    assert action.status == ActionStatus.COMPLETED
    assert action.tool_output == {"ok": True, "tool": "browser_click"}


def test_worker_rejects_terminal_action():
    action = make_action(ActionStatus.COMPLETED)
    with pytest.raises(ValueError, match="cannot execute"):
        ExecutionWorker(FakeExecutor()).execute_action(action)
