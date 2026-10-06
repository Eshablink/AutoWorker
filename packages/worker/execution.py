"""Deterministic worker execution contracts.

Actual browser/API/computer-use adapters will implement ToolExecutor later.
This layer owns execution orchestration, not tool-specific automation.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from packages.domain.models import ActionStatus, PolicyOutcome, TaskAction, ToolRisk


class ToolExecutionError(RuntimeError):
    """Raised when a registered tool fails during execution."""


@dataclass(frozen=True)
class ToolExecutionResult:
    output: Mapping[str, Any]
    observation: str


class ToolExecutor(Protocol):
    def execute(self, action: TaskAction) -> ToolExecutionResult:
        ...


class IdempotencyStore(Protocol):
    def get(self, key: str) -> ToolExecutionResult | None:
        ...

    def put(self, key: str, result: ToolExecutionResult) -> None:
        ...


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._results: dict[str, ToolExecutionResult] = {}

    def get(self, key: str) -> ToolExecutionResult | None:
        return self._results.get(key)

    def put(self, key: str, result: ToolExecutionResult) -> None:
        self._results[key] = result


class ExecutionWorker:
    def __init__(
        self,
        executor: ToolExecutor,
        idempotency_store: IdempotencyStore | None = None,
    ) -> None:
        self.executor = executor
        self.idempotency_store = idempotency_store or InMemoryIdempotencyStore()

    def execute_action(self, action: TaskAction) -> ToolExecutionResult:
        if action.status not in {ActionStatus.PENDING, ActionStatus.APPROVED}:
            raise ValueError(
                f"Action {action.action_id} cannot execute from status '{action.status.value}'."
            )

        policy = action.policy_decision
        if policy is not None and (
            policy.outcome == PolicyOutcome.REQUIRE_APPROVAL
            or policy.risk_level in {ToolRisk.HIGH, ToolRisk.CRITICAL}
        ):
            approval = action.approval_request
            if approval is None or approval.status.value != "APPROVED":
                raise PermissionError(
                    f"Action {action.action_id} cannot execute without approved HITL authorization."
                )

        if action.is_side_effecting and not (action.idempotency_key and action.idempotency_key.strip()):
            raise PermissionError(
                f"Action {action.action_id} cannot execute without an idempotency key."
            )

        if action.is_side_effecting and action.idempotency_key:
            existing = self.idempotency_store.get(action.idempotency_key)
            if existing is not None:
                action.tool_output = dict(existing.output)
                action.observation = existing.observation
                action.status = ActionStatus.COMPLETED
                return existing

        result = self.executor.execute(action)
        if action.is_side_effecting and action.idempotency_key:
            self.idempotency_store.put(action.idempotency_key, result)
        action.tool_output = dict(result.output)
        action.observation = result.observation
        action.status = ActionStatus.COMPLETED
        return result
