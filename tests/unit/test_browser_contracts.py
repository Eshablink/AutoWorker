from uuid import uuid4

import pytest

from packages.browser.contracts import BrowserLocator
from packages.browser.mock import MockBrowserAdapter


def test_mock_browser_observe_and_actions():
    session = MockBrowserAdapter().open(task_id=uuid4(), start_url="https://example.test")
    assert session.observe().url == "https://example.test"
    result = session.fill(BrowserLocator("css", "#invoice"), "INV-1")
    assert result.success is True
    assert result.output["action"] == "fill"


def test_closed_browser_rejects_operations():
    session = MockBrowserAdapter().open(task_id=uuid4())
    session.close()
    with pytest.raises(RuntimeError):
        session.observe()
