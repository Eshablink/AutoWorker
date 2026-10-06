"""LLM-agnostic agent contracts with an explicit structured-output boundary."""

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True)
class AgentRequest:
    task_id: UUID
    goal: str
    context: dict[str, Any] = field(default_factory=dict)
    request_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class ToolProposal:
    proposal_id: UUID = field(default_factory=uuid4)
    tool_id: str = ""
    input: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class AgentResponse:
    content: str
    proposals: tuple[ToolProposal, ...] = ()


class AgentProvider(Protocol):
    def complete(self, request: AgentRequest) -> AgentResponse:
        ...
