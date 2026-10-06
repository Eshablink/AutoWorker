"""Typed contracts for safe browser/computer-use adapters.

The domain depends on these contracts rather than a concrete browser vendor.
Implementations must keep side effects behind the execution/policy boundary.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class BrowserLocator:
    strategy: str
    value: str

    def __post_init__(self) -> None:
        if not self.strategy.strip() or not self.value.strip():
            raise ValueError("Browser locator strategy and value are required.")


@dataclass(frozen=True)
class BrowserObservation:
    session_id: UUID
    url: str
    title: str
    dom_snapshot: str | None = None
    screenshot_uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BrowserActionResult:
    success: bool
    observation: BrowserObservation
    output: dict[str, Any] = field(default_factory=dict)


class BrowserSession(Protocol):
    def observe(self) -> BrowserObservation:
        ...

    def click(self, locator: BrowserLocator) -> BrowserActionResult:
        ...

    def fill(self, locator: BrowserLocator, value: str) -> BrowserActionResult:
        ...

    def navigate(self, url: str) -> BrowserActionResult:
        ...

    def close(self) -> None:
        ...


class BrowserAdapter(Protocol):
    def open(self, *, task_id: UUID, start_url: str | None = None) -> BrowserSession:
        ...
