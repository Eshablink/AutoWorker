"""Deterministic policy engine for AutoWorker tool proposals."""

from dataclasses import dataclass
from typing import Iterable

from packages.domain.models import PolicyDecision, PolicyOutcome, Task, TaskAction, ToolRisk
from packages.tools.registry import ToolRegistry


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    reason: str


class PolicyEngine:
    """Evaluate a proposed action against deterministic safety rules.

    The engine does not execute tools or ask an LLM to make authorization decisions.
    """

    def __init__(self, registry: ToolRegistry, rules: Iterable[PolicyRule] = ()) -> None:
        self.registry = registry
        self.rules = tuple(rules)

    def evaluate(self, task: Task, action: TaskAction) -> PolicyDecision:
        tool = self.registry.get(action.tool_id)
        if action.task_id != task.task_id:
            raise ValueError("Action task_id does not match Task task_id.")

        outcome = PolicyOutcome.ALLOW
        reason = "Tool is registered and action passed baseline policy checks."
        evaluated_rules = [rule.rule_id for rule in self.rules]

        risk = tool.risk_level

        if risk in {ToolRisk.HIGH, ToolRisk.CRITICAL}:
            outcome = PolicyOutcome.REQUIRE_APPROVAL
            reason = f"Tool risk level is {risk.value}; explicit human approval is required."

        if tool.is_side_effecting and tool.requires_idempotency_key:
            if not action.idempotency_key or not action.idempotency_key.strip():
                outcome = PolicyOutcome.DENY
                reason = "Side-effecting tool requires a non-empty idempotency key."

        return PolicyDecision(
            task_id=task.task_id,
            action_id=action.action_id,
            tool_id=tool.tool_id,
            outcome=outcome,
            risk_level=risk,
            reason=reason,
            evaluated_rules=evaluated_rules,
        )
