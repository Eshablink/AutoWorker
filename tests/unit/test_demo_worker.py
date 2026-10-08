from uuid import uuid4

from packages.domain.models import Task, TaskStatus
from packages.persistence.memory import InMemoryTaskRepository
from packages.policy.engine import PolicyEngine
from packages.worker.execution import ExecutionWorker
from packages.worker.orchestrator import TaskOrchestrator
from packages.worker.runtime import WorkerRuntime
from packages.worker.demo import build_demo_components


def build_runtime():
    registry, planner, executor, checks = build_demo_components()
    task = Task(goal="Process invoice INV-42 total 250 INR")
    repository = InMemoryTaskRepository()
    repository.create(task)
    orchestrator = TaskOrchestrator(
        registry,
        PolicyEngine(registry),
        ExecutionWorker(executor),
    )
    return WorkerRuntime(
        repository,
        planner,
        orchestrator,
        worker_id="demo-test",
        verification_checks=lambda _task: checks,
    ), task


def test_demo_runtime_completes_invoice_and_verifies():
    worker, task = build_runtime()

    result = worker.run_once()

    assert result is not None
    assert result.status == TaskStatus.COMPLETED
    stored = worker.repository.get(task.task_id)
    assert stored.status == TaskStatus.COMPLETED
    assert stored.verification_result is not None
    assert stored.verification_result.success is True
    assert stored.actions[0].tool_output["status"] == "POSTED"


def test_demo_planner_supports_non_invoice_goals():
    registry, planner, executor, checks = build_demo_components()
    task = Task(goal="Check the system safely")
    actions = planner.build_actions(task)

    assert len(actions) == 1
    assert actions[0].tool_id == "acknowledge_goal"
    assert actions[0].idempotency_key == f"task:{task.task_id}:step:1"
