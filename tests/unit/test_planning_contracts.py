from uuid import uuid4

import pytest

from packages.planning.contracts import (
    ExecutionPlan,
    PlanStep,
    PlanValidationError,
    validate_plan,
)


def test_valid_plan_is_accepted():
    plan = ExecutionPlan(
        task_id=uuid4(),
        steps=(
            PlanStep(step_number=1, tool_id="extract_invoice", objective="Extract invoice data"),
            PlanStep(step_number=2, tool_id="verify_record", objective="Verify ERP record"),
        ),
    )
    validate_plan(plan)


def test_plan_rejects_gaps_and_empty_tool_ids():
    plan = ExecutionPlan(
        task_id=uuid4(),
        steps=(PlanStep(step_number=2, tool_id="", objective="Do something"),),
    )
    with pytest.raises(PlanValidationError):
        validate_plan(plan)
