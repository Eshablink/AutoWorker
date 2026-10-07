import pytest
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from packages.domain.models import (
    ActionStatus,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    PolicyDecision,
    PolicyOutcome,
    Task,
    TaskAction,
    ToolRisk,
)
from packages.domain.repository import ConcurrentUpdateError
from packages.persistence.sqlalchemy import Base, SqlAlchemyTaskRepository


@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield SqlAlchemyTaskRepository(session)
        session.rollback()


def audit(task):
    return AuditEvent(task_id=task.task_id, event_type="TEST", actor="pytest")


def test_sqlalchemy_repository_round_trip(repo):
    task = repo.create(Task(goal="Process invoice"))
    repo.session.commit()
    loaded = repo.get(task.task_id)
    assert loaded.goal == "Process invoice"


def test_sqlalchemy_repository_lists_newest_tasks_first(repo):
    older = Task(goal="Older operational task")
    newer = Task(
        goal="Newer operational task",
        created_at=older.created_at + timedelta(seconds=1),
        updated_at=older.updated_at + timedelta(seconds=1),
    )
    repo.create(older)
    repo.create(newer)
    repo.session.commit()

    tasks = repo.list_tasks(limit=2)
    assert [task.task_id for task in tasks] == [newer.task_id, older.task_id]


def test_sqlalchemy_repository_rejects_stale_version(repo):
    task = repo.create(Task(goal="Process invoice"))
    repo.session.commit()
    loaded = repo.get(task.task_id)
    loaded.version = 2
    repo.save(loaded, audit(loaded), expected_version=1)
    repo.session.commit()

    stale = repo.get(task.task_id)
    with pytest.raises(ConcurrentUpdateError):
        repo.save(stale, audit(stale), expected_version=1)


def test_sqlalchemy_repository_uses_approval_projection_for_lookup(repo):
    task = Task(goal="Approve invoice safely")
    action = TaskAction(
        task_id=task.task_id,
        step_number=1,
        tool_id="erp_submit",
        decision_summary="Submit invoice",
        status=ActionStatus.WAITING_APPROVAL,
    )
    action.policy_decision = PolicyDecision(
        task_id=task.task_id,
        action_id=action.action_id,
        tool_id=action.tool_id,
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        risk_level=ToolRisk.HIGH,
        reason="Financial write requires approval.",
    )
    approval = ApprovalRequest(
        task_id=task.task_id,
        action_id=action.action_id,
        policy_decision_id=action.policy_decision.decision_id,
        requested_action_name="Submit invoice",
        tool_id="erp_submit",
        payload_summary={"invoice": "INV-1"},
        risk_level=ToolRisk.HIGH,
        reason_required="Financial write",
    )
    action.approval_request = approval
    task.actions = [action]

    repo.create(task)
    repo.session.commit()

    loaded = repo.find_by_approval_id(approval.approval_id)
    assert loaded.task_id == task.task_id


def test_sqlalchemy_repository_updates_approval_projection_on_decision(repo):
    task = Task(goal="Approve invoice safely")
    action = TaskAction(
        task_id=task.task_id,
        step_number=1,
        tool_id="erp_submit",
        decision_summary="Submit invoice",
        status=ActionStatus.WAITING_APPROVAL,
    )
    action.policy_decision = PolicyDecision(
        task_id=task.task_id,
        action_id=action.action_id,
        tool_id=action.tool_id,
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        risk_level=ToolRisk.HIGH,
        reason="Financial write requires approval.",
    )
    approval = ApprovalRequest(
        task_id=task.task_id,
        action_id=action.action_id,
        policy_decision_id=action.policy_decision.decision_id,
        requested_action_name="Submit invoice",
        tool_id="erp_submit",
        payload_summary={},
        risk_level=ToolRisk.HIGH,
        reason_required="Financial write",
    )
    action.approval_request = approval
    task.actions = [action]

    repo.create(task)
    repo.session.commit()

    approval.status = ApprovalStatus.APPROVED
    approval.decided_at = approval.created_at + timedelta(seconds=1)
    action.status = ActionStatus.APPROVED
    task.status = TaskStatus.RUNNING
    task.version = 2
    repo.save(task, audit(task), expected_version=1)
    repo.session.commit()

    row = repo.session.get(__import__("packages.persistence.sqlalchemy", fromlist=["ApprovalRecord"]).ApprovalRecord, str(approval.approval_id))
    assert row.status == ApprovalStatus.APPROVED.value
