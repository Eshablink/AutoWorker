"""Deterministic worker execution contracts.

Actual browser/API/computer-use adapters will implement ToolExecutor later.
This layer owns execution orchestration, not tool-specific automation.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from packages.domain.models import ActionStatus, TaskAction


class ToolExecutionError(RuntimeError):
    """Raised when a registered tool fails during execution."""


@dataclass(frozen=True)
class ToolExecutionResult:
    output: Mapping[str, Any]
    observation: str


class ToolExecutor(Protocol):
    def execute(self, action: TaskAction) -> ToolExecutionResult:
        ...


class ExecutionWorker:
    def __init__(self, executor: ToolExecutor) -> None:
        self.executor = executor

    def execute_action(self, action: TaskAction) -> ToolExecutionResult:
        if action.status not in {ActionStatus.PENDING, ActionStatus.APPROVED}:
            raise ValueError(
                f"Action {action.action_id} cannot execute from status '{action.status.value}'."
            )

        result = self.executor.execute(action)
        action.tool_output = dict(result.output)
        action.observation = result.observation
        action.status = ActionStatus.COMPLETED
        return result
