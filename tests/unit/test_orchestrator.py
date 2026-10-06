import pytest

from packages.domain.models import Task, TaskAction, TaskStatus, ToolRisk, ToolDefinition
from packages.policy.engine import PolicyEngine
from packages.tools.registry import ToolRegistry
from packages.worker.execution import ExecutionWorker, ToolExecutionResult
from packages.worker.orchestrator import TaskOrchestrator
from packages.verification.engine import VerificationCheck


class FakeExecutor:
    def execute(self, action):
        return ToolExecutionResult(output={"ok": True}, observation="done")


def make_task():
    task = Task(goal="Process an invoice", status=TaskStatus.READY)
    task.actions = [
        TaskAction(
            task_id=task.task_id,
            step_number=1,
            tool_id="safe_tool",
            decision_summary="Execute safe tool",
        )
    ]
    return task


def test_orchestrator_prepares_and_executes():
    registry = ToolRegistry([
        ToolDefinition(
            tool_id="safe_tool",
            name="Safe",
            description="Safe test tool",
            input_schema={},
            output_schema={},
        )
    ])
    orchestrator = TaskOrchestrator(
        registry,
        PolicyEngine(registry),
        ExecutionWorker(FakeExecutor()),
    )
    task = make_task()

    orchestrator.prepare(task)
    assert task.status == TaskStatus.RUNNING

    result = orchestrator.execute_current(task)
    assert result.output["ok"] is True
    assert task.actions[0].status.value == "COMPLETED"


def test_orchestrator_routes_high_risk_to_approval():
    registry = ToolRegistry([
        ToolDefinition(
            tool_id="dangerous_tool",
            name="Dangerous",
            description="Requires approval",
            input_schema={},
            output_schema={},
            risk_level=ToolRisk.HIGH,
            is_side_effecting=True,
            requires_idempotency_key=True,
        )
    ])
    orchestrator = TaskOrchestrator(
        registry,
        PolicyEngine(registry),
        ExecutionWorker(FakeExecutor()),
    )
    task = make_task()
    task.actions[0].tool_id = "dangerous_tool"
    task.actions[0].idempotency_key = "test-key"

    orchestrator.prepare(task)

    assert task.status == TaskStatus.WAITING_APPROVAL
    assert task.actions[0].status.value == "WAITING_APPROVAL"


def test_orchestrator_requires_actions():
    registry = ToolRegistry([])
    orchestrator = TaskOrchestrator(
        registry,
        PolicyEngine(registry),
        ExecutionWorker(FakeExecutor()),
    )
    task = Task(goal="Process invoice", status=TaskStatus.READY)

    with pytest.raises(ValueError, match="no actions"):
        orchestrator.prepare(task)


def test_orchestrator_verifies_and_completes():
    registry = ToolRegistry([
        ToolDefinition(
            tool_id="safe_tool",
            name="Safe",
            description="Safe test tool",
            input_schema={},
            output_schema={},
        )
    ])
    orchestrator = TaskOrchestrator(
        registry,
        PolicyEngine(registry),
        ExecutionWorker(FakeExecutor()),
    )
    task = make_task()
    orchestrator.prepare(task)
    orchestrator.execute_current(task)

    completed = orchestrator.verify_current(
        task,
        checks=[
            VerificationCheck(
                "output-present",
                lambda action: (bool(action.tool_output), {"present": True}),
            ),
            VerificationCheck(
                "observation-present",
                lambda action: (bool(action.observation), {"present": True}),
            ),
        ],
    )

    assert completed.status == TaskStatus.COMPLETED
    assert completed.verification_result is not None
    assert completed.verification_result.success is True
