"""Optional Playwright-backed browser session adapter.

Playwright is intentionally imported lazily so the core API, tests, and policy
layers do not require a browser runtime.
"""

from typing import Any

from packages.tools.browser import (
    BrowserAction,
    BrowserActionResult,
    BrowserElement,
    BrowserObservation,
    BrowserSession,
    BrowserToolError,
)


class PlaywrightBrowserSession(BrowserSession):
    def __init__(self, page: Any) -> None:
        self.page = page

    @classmethod
    def launch(cls, url: str, *, headless: bool = True) -> "PlaywrightBrowserSession":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserToolError(
                "Playwright is not installed. Install the browser extra to use this adapter."
            ) from exc

        runtime = sync_playwright().start()
        browser = runtime.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        session = cls(page)
        session._runtime = runtime
        session._browser = browser
        return session

    def observe(self) -> BrowserObservation:
        url = self.page.url
        title = self.page.title()
        return BrowserObservation(url=url, title=title)

    def execute(self, action: BrowserAction) -> BrowserActionResult:
        if action.operation == "navigate":
            if not action.value:
                raise BrowserToolError("Navigate actions require a URL.")
            self.page.goto(action.value, wait_until="domcontentloaded", timeout=action.timeout_seconds * 1000)
        elif action.operation == "click":
            if action.target is None:
                raise BrowserToolError("Click actions require a target element.")
            self.page.locator(f'[data-autoworker-id="{action.target.element_id}"]').click(
                timeout=action.timeout_seconds * 1000
            )
        elif action.operation == "fill":
            if action.target is None or action.value is None:
                raise BrowserToolError("Fill actions require a target and value.")
            self.page.locator(f'[data-autoworker-id="{action.target.element_id}"]').fill(
                action.value,
                timeout=action.timeout_seconds * 1000,
            )
        else:
            raise BrowserToolError(f"Unsupported browser operation: {action.operation}")

        return BrowserActionResult(success=True, observation=self.observe())

    def close(self) -> None:
        browser = getattr(self, "_browser", None)
        runtime = getattr(self, "_runtime", None)
        if browser is not None:
            browser.close()
        if runtime is not None:
            runtime.stop()
