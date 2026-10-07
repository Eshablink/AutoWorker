from packages.audit.events import EventType
from packages.domain.models import Task, TaskAction, TaskStatus, ToolDefinition
from packages.persistence.memory import InMemoryTaskRepository
from packages.policy.engine import PolicyEngine
from packages.tools.registry import ToolRegistry
from packages.worker.execution import ExecutionWorker, ToolExecutionResult
from packages.worker.orchestrator import TaskOrchestrator
from packages.worker.runtime import WorkerRuntime
from packages.verification.engine import VerificationCheck


class FakePlanner:
    def build_actions(self, task):
        return [
            TaskAction(
                task_id=task.task_id,
                step_number=1,
                tool_id="safe_tool",
                decision_summary="Execute safe tool",
            )
        ]


class FakeExecutor:
    def execute(self, action):
        return ToolExecutionResult(output={"ok": True}, observation="done")


def runtime() -> WorkerRuntime:
    registry = ToolRegistry(
        [
            ToolDefinition(
                tool_id="safe_tool",
                name="Safe",
                description="Safe test tool",
                input_schema={},
                output_schema={},
            )
        ]
    )
    orchestrator = TaskOrchestrator(
        registry,
        PolicyEngine(registry),
        ExecutionWorker(FakeExecutor()),
    )
    repository = InMemoryTaskRepository()

    return WorkerRuntime(
        repository,
        FakePlanner(),
        orchestrator,
        worker_id="test-worker",
        verification_checks=lambda _task: [
            VerificationCheck("output", lambda action: (bool(action.tool_output), {"present": True}))
        ],
    )


def test_worker_runtime_plans_executes_verifies_and_persists_audit():
    worker = runtime()
    task = Task(goal="Process invoice safely")
    worker.repository.create(task)

    first = worker.run_once()
    assert first is not None
    assert first.status == TaskStatus.COMPLETED
    assert first.stage == "verification"

    stored = worker.repository.get(task.task_id)
    assert stored.status == TaskStatus.COMPLETED
    event_types = [event.event_type for event in worker.repository.list_audit(task.task_id)]
    assert EventType.ACTION_COMPLETED.value in event_types
    assert EventType.VERIFICATION_COMPLETED.value in event_types


def test_worker_runtime_returns_none_when_no_eligible_tasks():
    worker = runtime()
    task = Task(goal="Already completed", status=TaskStatus.COMPLETED)
    worker.repository.create(task)

    assert worker.run_once() is None


def test_worker_runtime_fails_empty_plan_without_getting_stuck():
    worker = runtime()

    class EmptyPlanner:
        def build_actions(self, task):
            return []

    worker.planner = EmptyPlanner()
    task = Task(goal="Plan this task safely")
    worker.repository.create(task)

    result = worker.run_once()
    assert result.status == TaskStatus.FAILED
    assert worker.repository.get(task.task_id).status == TaskStatus.FAILED


def test_worker_runtime_recovers_failed_read_only_action():
    worker = runtime()

    class FailingExecutor:
        def execute(self, action):
            raise RuntimeError("temporary browser failure")

    worker.orchestrator.worker = ExecutionWorker(FailingExecutor())
    task = Task(goal="Recover a safe browser operation")
    action = TaskAction(
        task_id=task.task_id,
        step_number=1,
        tool_id="safe_tool",
        decision_summary="Execute safe tool",
        status=__import__("packages.domain.models", fromlist=["ActionStatus"]).ActionStatus.PENDING,
        policy_decision=None,
    )
    # Start from READY so this test focuses on execution/recovery.
    task.status = TaskStatus.READY
    task.actions = [action]
    worker.repository.create(task)
    # Prepare binds the policy before execution.
    result = worker.run_once()
    assert result is not None
    assert result.status == TaskStatus.RECOVERING
