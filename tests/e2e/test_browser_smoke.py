from uuid import uuid4

from packages.tools.browser import BrowserAction, BrowserElement
from packages.tools.playwright import PlaywrightBrowserSession


def test_controlled_browser_executes_fill_and_click():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page()
        session = PlaywrightBrowserSession(
            page,
            allowed_origins=frozenset({"http://autoworker.local"}),
        )
        page.set_content(
            """
            <html>
              <head><title>Controlled ERP</title></head>
              <body>
                <input data-autoworker-id="invoice-number" />
                <button data-autoworker-id="submit-invoice"
                        onclick="document.body.dataset.submitted='true'">Submit</button>
              </body>
            </html>
            """
        )
        task_id = uuid4()
        action_id = uuid4()
        session.execute(
            BrowserAction(
                task_id=task_id,
                action_id=action_id,
                operation="fill",
                target=BrowserElement(
                    element_id="invoice-number",
                    role="textbox",
                ),
                value="INV-42",
            )
        )
        session.execute(
            BrowserAction(
                task_id=task_id,
                action_id=uuid4(),
                operation="click",
                target=BrowserElement(
                    element_id="submit-invoice",
                    role="button",
                ),
            )
        )

        assert page.locator('[data-autoworker-id="invoice-number"]').input_value() == "INV-42"
        assert page.locator("body").get_attribute("data-submitted") == "true"
        session.close()
