"""Reference worker runtime that connects durable tasks to the execution lifecycle.

The runtime intentionally keeps storage and adapters injectable. It can be used
with the in-memory repository for local demonstrations and with the SQLAlchemy
repository from a long-running worker process.
"""

from dataclasses import dataclass
from typing import Callable, Protocol
from uuid import UUID

from packages.audit.events import EventType
from packages.domain.models import AuditEvent, Task, TaskStatus
from packages.domain.repository import TaskRepository
from packages.domain.state import TaskStateMachine
from packages.verification.engine import VerificationCheck
from packages.worker.lease import InMemoryLeaseManager
from packages.worker.orchestrator import TaskOrchestrator
from packages.worker.recovery import RecoveryCoordinator


class TaskPlanner(Protocol):
    def build_actions(self, task: Task): ...


VerificationCheckFactory = Callable[[Task], list[VerificationCheck]]


@dataclass(frozen=True)
class WorkerRunResult:
    task_id: UUID
    status: TaskStatus
    progressed: bool
    stage: str
    error: str | None = None


class WorkerRuntime:
    """Process one eligible task at a time under a worker lease."""

    ELIGIBLE_STATUSES = {
        TaskStatus.CREATED,
        TaskStatus.READY,
        TaskStatus.RUNNING,
        TaskStatus.RECOVERING,
    }

    def __init__(
        self,
        repository: TaskRepository,
        planner: TaskPlanner,
        orchestrator: TaskOrchestrator,
        *,
        lease_manager: InMemoryLeaseManager | None = None,
        recovery: RecoveryCoordinator | None = None,
        worker_id: str = "worker-runtime",
        verification_checks: VerificationCheckFactory | None = None,
        lease_seconds: int = 30,
    ) -> None:
        if not worker_id.strip():
            raise ValueError("worker_id cannot be empty.")
        self.repository = repository
        self.planner = planner
        self.orchestrator = orchestrator
        self.lease_manager = lease_manager or InMemoryLeaseManager(lease_seconds=lease_seconds)
        self.recovery = recovery or RecoveryCoordinator()
        self.worker_id = worker_id.strip()
        self.verification_checks = verification_checks or (lambda _task: [])

    def run_once(self) -> WorkerRunResult | None:
        candidates = [
            task
            for task in self.repository.list_tasks(limit=50)
            if task.status in self.ELIGIBLE_STATUSES
        ]
        if not candidates:
            return None

        task_id = candidates[0].task_id
        lease = self.lease_manager.acquire(task_id, self.worker_id)
        try:
            task = self.repository.get(task_id)
            return self._run_task(task)
        finally:
            self.lease_manager.release(lease)

    def _run_task(self, task: Task) -> WorkerRunResult:
        if task.status == TaskStatus.CREATED:
            task = self._plan(task)
            if task.status != TaskStatus.READY:
                return WorkerRunResult(task.task_id, task.status, True, "planning", task.error_message)

        if task.status == TaskStatus.RECOVERING:
            before_version = task.version
            task, audit = TaskStateMachine.transition(
                task,
                TaskStatus.RUNNING,
                actor="WORKER_RUNTIME",
                reason="Resume action after bounded recovery.",
            )
            self.repository.save(task, audit, expected_version=before_version)

        if task.status == TaskStatus.READY:
            task = self._prepare(task)
            if task.status != TaskStatus.RUNNING:
                return WorkerRunResult(task.task_id, task.status, True, "policy", task.error_message)

        if task.status == TaskStatus.RUNNING:
            return self._execute_and_verify(task)

        return WorkerRunResult(task.task_id, task.status, False, "idle", task.error_message)

    def _plan(self, task: Task) -> Task:
        before_version = task.version
        task, audit = TaskStateMachine.transition(
            task,
            TaskStatus.PLANNING,
            actor="WORKER_RUNTIME",
            reason="Worker claimed task for planning.",
        )
        self.repository.save(task, audit, expected_version=before_version)

        try:
            actions = list(self.planner.build_actions(task))
        except Exception as exc:
            task.error_message = f"Planning failed: {exc}"
            before_failure = task.version
            task, failure_audit = TaskStateMachine.transition(
                task,
                TaskStatus.FAILED,
                actor="WORKER_RUNTIME",
                reason=task.error_message,
            )
            self.repository.save(task, failure_audit, expected_version=before_failure)
            return task

        if not actions:
            task.error_message = "Planning produced no executable actions."
            before_failure = task.version
            task, failure_audit = TaskStateMachine.transition(
                task,
                TaskStatus.FAILED,
                actor="WORKER_RUNTIME",
                reason=task.error_message,
            )
            self.repository.save(task, failure_audit, expected_version=before_failure)
            return task

        task.actions = actions
        before_ready = task.version
        task, ready_audit = TaskStateMachine.transition(
            task,
            TaskStatus.READY,
            actor="WORKER_RUNTIME",
            reason=f"Planning produced {len(actions)} executable actions.",
        )
        self.repository.save(task, ready_audit, expected_version=before_ready)
        return task

    def _prepare(self, task: Task) -> Task:
        before_version = task.version
        prepared = self.orchestrator.prepare(task)
        if prepared.status == TaskStatus.WAITING_APPROVAL:
            action = prepared.actions[prepared.current_step_index]
            audit = AuditEvent(
                task_id=prepared.task_id,
                action_id=action.action_id,
                event_type=EventType.APPROVAL_REQUIRED.value,
                actor="WORKER_RUNTIME",
                details={
                    "approval_id": str(action.approval_request.approval_id)
                    if action.approval_request
                    else None,
                    "tool_id": action.tool_id,
                    "reason": action.policy_decision.reason if action.policy_decision else None,
                },
            )
        elif prepared.status == TaskStatus.FAILED:
            audit = AuditEvent(
                task_id=prepared.task_id,
                event_type=EventType.ACTION_FAILED.value,
                actor="WORKER_RUNTIME",
                details={"reason": prepared.error_message or "Policy denied execution."},
            )
        else:
            audit = AuditEvent(
                task_id=prepared.task_id,
                event_type=EventType.TASK_STATE_CHANGED.value,
                actor="WORKER_RUNTIME",
                details={"status": prepared.status.value},
            )
        self.repository.save(prepared, audit, expected_version=before_version)
        return prepared

    def _execute_and_verify(self, task: Task) -> WorkerRunResult:
        before_execution = task.version
        action = task.actions[task.current_step_index]
        try:
            self.orchestrator.execute_current(task)
        except Exception as exc:
            self.repository.save(
                task,
                AuditEvent(
                    task_id=task.task_id,
                    action_id=action.action_id,
                    event_type=EventType.ACTION_FAILED.value,
                    actor="WORKER_RUNTIME",
                    details={"error": str(exc)},
                ),
                expected_version=before_execution,
            )
            try:
                before_recovery = task.version
                recovered = self.recovery.recover(task)
                self.repository.save(
                    recovered,
                    AuditEvent(
                        task_id=recovered.task_id,
                        action_id=action.action_id,
                        event_type=EventType.RECOVERY_STARTED.value,
                        actor="WORKER_RUNTIME",
                        details={"retry_count": action.retry_count, "status": recovered.status.value},
                    ),
                    expected_version=before_recovery,
                )
                return WorkerRunResult(
                    task.task_id,
                    recovered.status,
                    True,
                    "recovery",
                    recovered.error_message,
                )
            except Exception as recovery_error:
                return WorkerRunResult(
                    task.task_id,
                    task.status,
                    True,
                    "execution",
                    str(recovery_error),
                )

        self.repository.save(
            task,
            AuditEvent(
                task_id=task.task_id,
                action_id=action.action_id,
                event_type=EventType.ACTION_COMPLETED.value,
                actor="WORKER_RUNTIME",
                details={"status": action.status.value},
            ),
            expected_version=before_execution,
        )

        try:
            before_verification = task.version
            verified = self.orchestrator.verify_current(
                task,
                checks=self.verification_checks(task),
            )
        except Exception as exc:
            task.error_message = f"Verification lifecycle failed: {exc}"
            if task.status == TaskStatus.FAILED:
                failure_audit = AuditEvent(
                    task_id=task.task_id,
                    event_type=EventType.ACTION_FAILED.value,
                    actor="WORKER_RUNTIME",
                    details={"error": task.error_message},
                )
            else:
                task, failure_audit = TaskStateMachine.transition(
                    task,
                    TaskStatus.FAILED,
                    actor="WORKER_RUNTIME",
                    reason=task.error_message,
                )
            self.repository.save(task, failure_audit, expected_version=before_verification)
            return WorkerRunResult(task.task_id, task.status, True, "verification", task.error_message)

        self.repository.save(
            verified,
            AuditEvent(
                task_id=verified.task_id,
                action_id=action.action_id,
                event_type=EventType.VERIFICATION_COMPLETED.value,
                actor="WORKER_RUNTIME",
                details={
                    "status": verified.status.value,
                    "verification": (
                        verified.verification_result.model_dump(mode="json")
                        if verified.verification_result
                        else None
                    ),
                },
            ),
            expected_version=before_verification,
        )
        return WorkerRunResult(verified.task_id, verified.status, True, "verification", verified.error_message)
