"""Deterministic demo composition for a truthful end-to-end AutoWorker run.

The demo uses the repository's controlled SimulatedERP adapter. It is intentionally
not an LLM or external automation provider; it exists so the durable execution
pipeline can be exercised end-to-end without unsafe side effects.
"""

from __future__ import annotations

import re

from packages.domain.models import Task, TaskAction, ToolDefinition, ToolRisk
from packages.integrations.simulated_erp import SimulatedERP
from packages.tools.erp import ERPWriteRequest
from packages.tools.registry import ToolRegistry
from packages.verification.engine import VerificationCheck
from packages.worker.execution import ToolExecutionResult


class DemoPlanner:
    """Create one deterministic action from a task goal."""

    def build_actions(self, task: Task) -> list[TaskAction]:
        if "invoice" not in task.goal.lower():
            return [
                TaskAction(
                    task_id=task.task_id,
                    step_number=1,
                    tool_id="acknowledge_goal",
                    tool_input={"goal": task.goal},
                    decision_summary="Acknowledge the requested goal in the controlled demo runtime.",
                    idempotency_key=f"task:{task.task_id}:step:1",
                )
            ]

        invoice_number = self._extract(r"\b(?:invoice|inv)[\s:#-]*([A-Za-z0-9-]+)", task.goal)
        total_match = re.search(r"\b(?:total|amount)[\s:=₹$]*([0-9]+(?:\.[0-9]+)?)", task.goal, re.I)
        currency_match = re.search(r"\b(INR|USD|EUR|GBP)\b", task.goal, re.I)

        return [
            TaskAction(
                task_id=task.task_id,
                step_number=1,
                tool_id="create_simulated_invoice",
                tool_input={
                    "invoice_number": invoice_number or f"AW-{str(task.task_id)[:8].upper()}",
                    "vendor_name": "AutoWorker Demo Vendor",
                    "currency": (currency_match.group(1).upper() if currency_match else "INR"),
                    "total": float(total_match.group(1)) if total_match else 100.0,
                },
                is_side_effecting=True,
                idempotency_key=f"task:{task.task_id}:step:1",
                decision_summary="Create a simulated ERP invoice and verify the resulting record.",
            )
        ]

    @staticmethod
    def _extract(pattern: str, value: str) -> str | None:
        match = re.search(pattern, value, re.I)
        return match.group(1) if match else None


class DemoToolExecutor:
    """Execute only controlled, in-process demo tools."""

    def __init__(self, erp: SimulatedERP) -> None:
        self.erp = erp

    def execute(self, action) -> ToolExecutionResult:
        if action.tool_id == "acknowledge_goal":
            return ToolExecutionResult(
                output={"accepted": True, "mode": "controlled-demo", "goal": action.tool_input["goal"]},
                observation="Goal acknowledged by the controlled demo executor.",
            )

        if action.tool_id == "create_simulated_invoice":
            request = ERPWriteRequest(
                task_id=action.task_id,
                action_id=action.action_id,
                invoice_number=str(action.tool_input["invoice_number"]),
                vendor_name=str(action.tool_input["vendor_name"]),
                currency=str(action.tool_input["currency"]).upper(),
                total=float(action.tool_input["total"]),
                idempotency_key=str(action.idempotency_key),
            )
            result = self.erp.create_invoice(request)
            if not result.accepted or result.record is None:
                raise RuntimeError(
                    "Simulated ERP rejected invoice: "
                    + ", ".join(result.validation_errors)
                )
            return ToolExecutionResult(
                output={
                    "external_id": result.record.external_id,
                    "invoice_number": result.record.invoice_number,
                    "status": result.record.status,
                    "total": result.record.total,
                    "currency": result.record.currency,
                },
                observation=f"Simulated ERP posted {result.record.external_id}.",
            )

        raise ValueError(f"Demo tool '{action.tool_id}' is not registered.")


def build_demo_components() -> tuple[ToolRegistry, DemoPlanner, DemoToolExecutor, list[VerificationCheck]]:
    erp = SimulatedERP()
    registry = ToolRegistry(
        [
            ToolDefinition(
                tool_id="acknowledge_goal",
                name="Acknowledge Goal",
                description="Record a deterministic acknowledgement in the controlled demo runtime.",
                input_schema={"type": "object", "required": ["goal"]},
                output_schema={"type": "object"},
                risk_level=ToolRisk.LOW,
                is_side_effecting=False,
            ),
            ToolDefinition(
                tool_id="create_simulated_invoice",
                name="Create Simulated Invoice",
                description="Create an invoice in the in-process simulated ERP.",
                input_schema={
                    "type": "object",
                    "required": ["invoice_number", "vendor_name", "currency", "total"],
                },
                output_schema={"type": "object"},
                risk_level=ToolRisk.LOW,
                is_side_effecting=True,
                requires_idempotency_key=True,
            ),
        ]
    )
    executor = DemoToolExecutor(erp)

    def verify_output(action):
        output = action.tool_output or {}
        if action.tool_id == "create_simulated_invoice":
            external_id = output.get("external_id")
            record = erp.get_invoice(str(external_id)) if external_id else None
            return record is not None and record.status == "POSTED", {
                "external_id": external_id,
                "erp_status": record.status if record else None,
            }
        return bool(output.get("accepted")), {"accepted": output.get("accepted")}

    return registry, DemoPlanner(), executor, [
        VerificationCheck("controlled_execution", verify_output)
    ]
