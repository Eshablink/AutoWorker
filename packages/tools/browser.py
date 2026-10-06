"""Safe browser/computer-use tool contracts.

The browser layer is an adapter boundary: policy and orchestration decide whether
an action may run, while concrete Playwright/computer-use implementations live
outside the domain layer.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID


class BrowserToolError(RuntimeError):
    """Base error for browser adapter failures."""


class BrowserTimeoutError(BrowserToolError):
    """Raised when a browser operation exceeds its deadline."""


@dataclass(frozen=True)
class BrowserElement:
    element_id: str
    role: str
    name: str | None = None
    text: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class BrowserObservation:
    url: str
    title: str
    screenshot_ref: str | None = None
    dom_snapshot: str | None = None
    elements: tuple[BrowserElement, ...] = ()


@dataclass(frozen=True)
class BrowserAction:
    task_id: UUID
    action_id: UUID
    operation: str
    target: BrowserElement | None = None
    value: str | None = None
    timeout_seconds: int = 30
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.operation.strip():
            raise ValueError("Browser operation cannot be empty.")
        if not 1 <= self.timeout_seconds <= 300:
            raise ValueError("Browser action timeout must be between 1 and 300 seconds.")


@dataclass(frozen=True)
class BrowserActionResult:
    success: bool
    observation: BrowserObservation
    output: dict[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()


class BrowserSession(Protocol):
    def observe(self) -> BrowserObservation:
        ...

    def execute(self, action: BrowserAction) -> BrowserActionResult:
        ...

    def close(self) -> None:
        ...
