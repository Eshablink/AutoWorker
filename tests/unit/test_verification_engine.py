from packages.domain.models import TaskAction
from packages.verification.engine import VerificationCheck, VerificationEngine


def action():
    return TaskAction(
        task_id=__import__("uuid").uuid4(),
        step_number=1,
        tool_id="test",
        decision_summary="Run test",
    )


def test_verification_engine_passes_all_checks():
    item = action()
    item.tool_output = {"status": "processed"}
    item.observation = "Invoice processed successfully"
    result = VerificationEngine().verify(
        item.task_id,
        item,
        checks=[
            VerificationCheck("output-present", lambda a: (bool(a.tool_output), {"present": True})),
            VerificationCheck("observation-present", lambda a: (bool(a.observation), {"present": True})),
        ],
    )
    assert result.success is True
    assert result.confidence_score == 1.0


def test_verification_engine_reports_partial_failure():
    item = action()
    item.tool_output = {"id": "123"}
    result = VerificationEngine().verify(
        item.task_id,
        item,
        checks=[
            VerificationCheck("output", lambda a: (True, {"id": "123"})),
            VerificationCheck("external-record", lambda a: (False, {"found": False})),
        ],
    )
    assert result.success is False
    assert result.confidence_score == 0.5
