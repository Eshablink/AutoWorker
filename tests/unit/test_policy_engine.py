import pytest

from packages.domain.models import PolicyOutcome, Task, TaskAction, ToolRisk, ToolDefinition
from packages.policy.engine import PolicyEngine, PolicyRule
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


def test_payload_aware_rule_can_deny_action_and_records_policy_version():
    registry = ToolRegistry(
        [
            ToolDefinition(
                tool_id="refund",
                name="Refund",
                description="Refund a customer",
                input_schema={},
                output_schema={},
                is_side_effecting=True,
                requires_idempotency_key=True,
            )
        ]
    )
    task = Task(goal="Process a refund safely")
    action = TaskAction(
        task_id=task.task_id,
        step_number=1,
        tool_id="refund",
        idempotency_key="refund-1",
        decision_summary="Refund customer",
        tool_input={"amount": 50000},
    )
    engine = PolicyEngine(
        registry,
        rules=[
            PolicyRule(
                rule_id="refund-maximum",
                reason="Refund amount exceeds configured limit.",
                outcome=PolicyOutcome.DENY,
                matches=lambda _task, current_action, _tool: current_action.tool_input.get("amount", 0) > 10000,
            )
        ],
        policy_version="2026.1",
    )
    decision = engine.evaluate(task, action)
    assert decision.outcome == PolicyOutcome.DENY
    assert decision.policy_version == "2026.1"
    assert "refund-maximum" in decision.evaluated_rules
