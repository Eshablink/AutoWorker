"""Deterministic browser adapter for tests and local development."""

from uuid import UUID, uuid4

from packages.browser.contracts import BrowserActionResult, BrowserLocator, BrowserObservation


class MockBrowserSession:
    def __init__(self, start_url: str = "about:blank") -> None:
        self.session_id = uuid4()
        self.url = start_url
        self.title = ""
        self.closed = False

    def observe(self) -> BrowserObservation:
        self._ensure_open()
        return BrowserObservation(
            session_id=self.session_id,
            url=self.url,
            title=self.title,
            dom_snapshot="<mock-dom />",
        )

    def click(self, locator: BrowserLocator) -> BrowserActionResult:
        self._ensure_open()
        return BrowserActionResult(True, self.observe(), {"action": "click", "locator": locator.value})

    def fill(self, locator: BrowserLocator, value: str) -> BrowserActionResult:
        self._ensure_open()
        return BrowserActionResult(True, self.observe(), {"action": "fill", "locator": locator.value})

    def navigate(self, url: str) -> BrowserActionResult:
        self._ensure_open()
        if not url.strip():
            raise ValueError("Navigation URL cannot be empty.")
        self.url = url.strip()
        return BrowserActionResult(True, self.observe(), {"action": "navigate", "url": self.url})

    def close(self) -> None:
        self.closed = True

    def _ensure_open(self) -> None:
        if self.closed:
            raise RuntimeError("Browser session is closed.")


class MockBrowserAdapter:
    def open(self, *, task_id: UUID, start_url: str | None = None) -> MockBrowserSession:
        return MockBrowserSession(start_url or "about:blank")
