from fastapi.testclient import TestClient

from apps.api.main import app
from packages.domain.models import (
    ActionStatus,
    ApprovalRequest,
    PolicyDecision,
    PolicyOutcome,
    Task,
    TaskAction,
    TaskStatus,
    ToolRisk,
)
from packages.persistence.memory import InMemoryTaskRepository

from apps.api.database import get_task_repository


def test_health_endpoint():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "autoworker-api"}


def test_health_returns_request_correlation_id():
    response = TestClient(app).get("/health", headers={"X-Request-ID": "test-request-1"})
    assert response.headers["X-Request-ID"] == "test-request-1"


def test_health_generates_request_correlation_id():
    response = TestClient(app).get("/health")
    assert response.headers["X-Request-ID"]


def test_cors_allows_configured_local_frontend():
    response = TestClient(app).options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_operator_task_detail_exposes_actions(monkeypatch):
    repository = InMemoryTaskRepository()
    app.dependency_overrides[get_task_repository] = lambda: repository
    task = Task(goal="Inspect invoice task")
    action = TaskAction(
        task_id=task.task_id,
        step_number=1,
        tool_id="invoice_extract",
        decision_summary="Extract invoice",
        status=ActionStatus.COMPLETED,
        tool_output={"invoice_number": "INV-42"},
        observation="Invoice extracted.",
    )
    task.actions = [action]
    task.status = TaskStatus.RUNNING
    repository.create(task)

    response = TestClient(app).get(f"/tasks/{task.task_id}/detail")

    assert response.status_code == 200
    body = response.json()
    assert body["actions"][0]["tool_id"] == "invoice_extract"
    assert body["actions"][0]["tool_output"]["invoice_number"] == "INV-42"
    app.dependency_overrides.pop(get_task_repository, None)


def test_operator_approval_inbox_lists_pending_actions(monkeypatch):
    repository = InMemoryTaskRepository()
    task = Task(goal="Approve ERP invoice")
    action = TaskAction(
        task_id=task.task_id,
        step_number=1,
        tool_id="erp_submit",
        decision_summary="Submit invoice to ERP",
        status=ActionStatus.WAITING_APPROVAL,
    )
    action.policy_decision = PolicyDecision(
        task_id=task.task_id,
        action_id=action.action_id,
        tool_id=action.tool_id,
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        risk_level=ToolRisk.HIGH,
        reason="Financial write requires human approval.",
    )
    action.approval_request = ApprovalRequest(
        task_id=task.task_id,
        action_id=action.action_id,
        policy_decision_id=action.policy_decision.decision_id,
        requested_action_name="Submit invoice to ERP",
        tool_id=action.tool_id,
        payload_summary={"invoice_number": "INV-42", "amount": 1250},
        risk_level=ToolRisk.HIGH,
        reason_required="Financial write requires human approval.",
    )
    task.status = TaskStatus.WAITING_APPROVAL
    task.actions = [action]
    repository.create(task)

    app.dependency_overrides[get_task_repository] = lambda: repository
    try:
        response = TestClient(app).get("/approvals")
    finally:
        app.dependency_overrides.pop(get_task_repository, None)

    assert response.status_code == 200
    body = response.json()
    assert body[0]["approval_id"] == str(action.approval_request.approval_id)
    assert body[0]["risk_level"] == "HIGH"
