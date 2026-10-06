"""Deterministic planning contracts for LLM-backed and rule-based planners."""

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True)
class PlanStep:
    step_id: UUID = field(default_factory=uuid4)
    step_number: int = 1
    tool_id: str = ""
    objective: str = ""
    input_template: dict[str, Any] = field(default_factory=dict)
    side_effecting: bool = False
    requires_verification: bool = True


@dataclass(frozen=True)
class ExecutionPlan:
    task_id: UUID
    steps: tuple[PlanStep, ...]
    planner_version: str = "deterministic-v1"


class Planner(Protocol):
    def plan(self, task_id: UUID, goal: str, context: dict[str, Any]) -> ExecutionPlan:
        ...


class PlanValidationError(ValueError):
    """Raised when a planner produces an unsafe or malformed plan."""


def validate_plan(plan: ExecutionPlan) -> None:
    if not plan.steps:
        raise PlanValidationError("Execution plan must contain at least one step.")
    expected = 1
    for step in plan.steps:
        if step.step_number != expected:
            raise PlanValidationError("Plan step numbers must be contiguous and start at 1.")
        if not step.tool_id.strip() or not step.objective.strip():
            raise PlanValidationError("Every plan step requires a tool_id and objective.")
        expected += 1
