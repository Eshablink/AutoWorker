"""In-memory typed tool registry.

The registry is deliberately infrastructure-light. Tool execution belongs to the
worker layer; this module only defines and validates what may be executed.
"""

from typing import Dict, Iterable

from packages.domain.models import ToolDefinition


class ToolAlreadyRegisteredError(ValueError):
    """Raised when a tool ID is registered twice."""


class ToolNotFoundError(KeyError):
    """Raised when a requested tool does not exist."""


class ToolRegistry:
    def __init__(self, tools: Iterable[ToolDefinition] = ()) -> None:
        self._tools: Dict[str, ToolDefinition] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: ToolDefinition) -> None:
        if tool.tool_id in self._tools:
            raise ToolAlreadyRegisteredError(
                f"Tool '{tool.tool_id}' is already registered."
            )
        self._tools[tool.tool_id] = tool

    def get(self, tool_id: str) -> ToolDefinition:
        try:
            return self._tools[tool_id]
        except KeyError as exc:
            raise ToolNotFoundError(f"Tool '{tool_id}' is not registered.") from exc

    def list(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._tools.values())

    def contains(self, tool_id: str) -> bool:
        return tool_id in self._tools
