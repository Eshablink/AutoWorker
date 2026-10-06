from packages.tools.playwright import PlaywrightBrowserSession
from packages.tools.browser import BrowserAction
from uuid import uuid4


class FakePage:
    def __init__(self):
        self.url = "https://erp.local"
        self.actions = []

    def title(self):
        return "ERP"

    def goto(self, url, **kwargs):
        self.url = url
        self.actions.append(("goto", url, kwargs))


def test_playwright_adapter_observes_fake_page():
    session = PlaywrightBrowserSession(FakePage())
    observation = session.observe()
    assert observation.url == "https://erp.local"
    assert observation.title == "ERP"


def test_playwright_adapter_rejects_unknown_operation():
    session = PlaywrightBrowserSession(FakePage())
    action = BrowserAction(task_id=uuid4(), action_id=uuid4(), operation="delete_all")
    try:
        session.execute(action)
    except Exception as exc:
        assert "Unsupported browser operation" in str(exc)
    else:
        raise AssertionError("Expected unsupported operation to fail")


def test_playwright_adapter_blocks_unapproved_navigation():
    session = PlaywrightBrowserSession(FakePage(), allowed_origins=frozenset({"https://erp.local"}))
    action = BrowserAction(
        task_id=uuid4(),
        action_id=uuid4(),
        operation="navigate",
        value="https://example.com",
    )
    with pytest.raises(BrowserToolError, match="not allowed"):
        session.execute(action)
