from packages.agent.contracts import AgentRequest, AgentResponse, ToolProposal
from packages.agent.planner import AgentPlanner
from packages.domain.models import Task


class FakeProvider:
    def complete(self, request: AgentRequest) -> AgentResponse:
        return AgentResponse(
            content="Plan invoice processing.",
            proposals=(
                ToolProposal(tool_id="extract_invoice", reason="Extract invoice fields"),
                ToolProposal(tool_id="verify_invoice", reason="Verify extracted values"),
            ),
        )


def test_agent_planner_builds_typed_actions():
    task = Task(goal="Process the invoice safely")
    actions = AgentPlanner(FakeProvider()).build_actions(task)
    assert [action.step_number for action in actions] == [1, 2]
    assert [action.tool_id for action in actions] == ["extract_invoice", "verify_invoice"]
    assert all(action.task_id == task.task_id for action in actions)
