from uuid import uuid4

from packages.tools.browser import BrowserAction, BrowserElement, BrowserObservation


def test_browser_contracts_are_typed_and_immutable():
    task_id = uuid4()
    action_id = uuid4()
    element = BrowserElement(element_id="submit", role="button", name="Submit")
    action = BrowserAction(
        task_id=task_id,
        action_id=action_id,
        operation="click",
        target=element,
    )
    observation = BrowserObservation(url="https://erp.example", title="ERP")

    assert action.task_id == task_id
    assert action.target is element
    assert observation.url.startswith("https://")


def test_browser_action_timeout_has_safe_default():
    action = BrowserAction(task_id=uuid4(), action_id=uuid4(), operation="navigate")
    assert action.timeout_seconds == 30
