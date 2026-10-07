from uuid import uuid4

import pytest

from packages.domain.models import ActionStatus, TaskAction
from packages.worker.execution import ExecutionWorker, InMemoryIdempotencyStore, ToolExecutionResult


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
    assert action.started_at is not None
    assert action.completed_at is not None
    assert action.completed_at >= action.started_at


class FailingExecutor:
    def execute(self, action):
        raise RuntimeError("tool exploded")


def test_worker_marks_failed_execution():
    action = make_action()
    with pytest.raises(RuntimeError, match="tool exploded"):
        ExecutionWorker(FailingExecutor()).execute_action(action)
    assert action.status == ActionStatus.FAILED
    assert action.error_message == "tool exploded"
    assert action.started_at is not None
    assert action.completed_at is not None


def test_worker_rejects_terminal_action():
    action = make_action(ActionStatus.COMPLETED)
    with pytest.raises(ValueError, match="cannot execute"):
        ExecutionWorker(FakeExecutor()).execute_action(action)


def test_worker_rejects_side_effect_without_idempotency_key():
    action = make_action()
    action.is_side_effecting = True
    with pytest.raises(PermissionError, match="idempotency key"):
        ExecutionWorker(FakeExecutor()).execute_action(action)


def test_worker_rejects_high_risk_action_without_approval():
    from packages.domain.models import PolicyDecision, PolicyOutcome, ToolRisk

    action = make_action()
    action.policy_decision = PolicyDecision(
        task_id=action.task_id,
        action_id=action.action_id,
        tool_id=action.tool_id,
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        risk_level=ToolRisk.HIGH,
        reason="Human approval required.",
    )
    action.idempotency_key = "worker-test-1"
    with pytest.raises(PermissionError, match="approved HITL"):
        ExecutionWorker(FakeExecutor()).execute_action(action)


def test_side_effecting_action_reuses_idempotent_result_without_reexecuting():
    calls = []

    class CountingExecutor:
        def execute(self, action):
            calls.append(action.action_id)
            return ToolExecutionResult(output={"posted": True}, observation="Posted once")

    store = InMemoryIdempotencyStore()
    worker = ExecutionWorker(CountingExecutor(), store)
    action = TaskAction(
        task_id=uuid4(),
        step_number=1,
        tool_id="erp_submit",
        is_side_effecting=True,
        idempotency_key="invoice-101",
        decision_summary="Submit invoice",
    )
    first = worker.execute_action(action)
    action.status = ActionStatus.PENDING
    second = worker.execute_action(action)
    assert first == second
    assert len(calls) == 1
