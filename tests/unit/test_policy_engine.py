import pytest

from packages.domain.models import PolicyOutcome, Task, TaskAction, ToolRisk, ToolDefinition
from packages.policy.engine import PolicyEngine
from packages.tools.registry import ToolRegistry


def make_task():
    return Task(goal="Process and verify an invoice in the ERP system.")


def make_action(task, tool_id="browser_click", key=None):
    return TaskAction(
        task_id=task.task_id,
        step_number=1,
        tool_id=tool_id,
        is_side_effecting=key is not None,
        idempotency_key=key,
        decision_summary="Execute the registered tool.",
    )


def test_low_risk_action_is_allowed():
    task = make_task()
    registry = ToolRegistry([
        ToolDefinition(
            tool_id="browser_click",
            name="Browser Click",
            description="Click a browser target.",
            input_schema={},
            output_schema={},
            risk_level=ToolRisk.LOW,
        )
    ])
    decision = PolicyEngine(registry).evaluate(task, make_action(task))
    assert decision.outcome == PolicyOutcome.ALLOW


def test_high_risk_action_requires_approval():
    task = make_task()
    registry = ToolRegistry([
        ToolDefinition(
            tool_id="execute_refund",
            name="Execute Refund",
            description="Issue a refund.",
            input_schema={},
            output_schema={},
            risk_level=ToolRisk.HIGH,
            is_side_effecting=True,
            requires_idempotency_key=True,
        )
    ])
    action = make_action(task, "execute_refund", key="refund-123")
    decision = PolicyEngine(registry).evaluate(task, action)
    assert decision.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert decision.risk_level == ToolRisk.HIGH


def test_required_idempotency_missing_is_denied():
    task = make_task()
    registry = ToolRegistry([
        ToolDefinition(
            tool_id="execute_refund",
            name="Execute Refund",
            description="Issue a refund.",
            input_schema={},
            output_schema={},
            risk_level=ToolRisk.LOW,
            is_side_effecting=True,
            requires_idempotency_key=True,
        )
    ])
    action = make_action(task, "execute_refund")
    decision = PolicyEngine(registry).evaluate(task, action)
    assert decision.outcome == PolicyOutcome.DENY
    assert "idempotency" in decision.reason.lower()


def test_action_from_different_task_is_rejected():
    task = make_task()
    other = make_task()
    registry = ToolRegistry([make_tool := ToolDefinition(
        tool_id="browser_click",
        name="Browser Click",
        description="Click.",
        input_schema={},
        output_schema={},
    )])
    with pytest.raises(ValueError, match="does not match"):
        PolicyEngine(registry).evaluate(task, make_action(other, make_tool.tool_id))
