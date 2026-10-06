"""Structured agent-to-execution planning adapter."""

from packages.agent.contracts import AgentProvider
from packages.domain.models import Task, TaskAction


class AgentPlanner:
    """Turn provider proposals into validated TaskAction objects."""

    def __init__(self, provider: AgentProvider) -> None:
        self.provider = provider

    def build_actions(self, task: Task) -> list[TaskAction]:
        response = self.provider.complete(
            __import__("packages.agent.contracts", fromlist=["AgentRequest"]).AgentRequest(
                task_id=task.task_id,
                goal=task.goal,
                context=task.context_memory,
            )
        )
        if not response.proposals:
            raise ValueError("Agent returned no executable tool proposals.")

        actions: list[TaskAction] = []
        for index, proposal in enumerate(response.proposals, start=1):
            if not proposal.tool_id.strip():
                raise ValueError("Agent proposal is missing a tool_id.")
            actions.append(
                TaskAction(
                    task_id=task.task_id,
                    step_number=index,
                    tool_id=proposal.tool_id,
                    tool_input=proposal.input,
                    decision_summary=proposal.reason or response.content[:500],
                )
            )
        return actions
