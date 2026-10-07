from uuid import uuid4

from packages.tools.browser import BrowserAction, BrowserElement
from packages.tools.playwright import PlaywrightBrowserSession
from playwright.sync_api import sync_playwright


def test_controlled_browser_executes_fill_and_click():
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


def test_postgres_invoice_browser_integration():
    import os
    from sqlalchemy import create_engine

    from packages.domain.models import AuditEvent, Task
    from packages.persistence.sqlalchemy import SqlAlchemyTaskRepository
    from packages.integrations.simulated_erp import SimulatedERP
    from packages.tools.document import InvoiceExtraction
    from packages.workflows.invoice import InvoiceWorkflow

    engine = create_engine(os.environ["DATABASE_URL"])
    from sqlalchemy.orm import Session

    task = Task(goal="Process and verify invoice in controlled browser")
    with Session(engine) as session:
        repository = SqlAlchemyTaskRepository(session)
        repository.create(task)
        repository.append_audit(
            AuditEvent(
                task_id=task.task_id,
                event_type="E2E_STARTED",
                actor="E2E",
                details={"workflow": "invoice_browser"},
            )
        )
        session.commit()

    workflow = InvoiceWorkflow(SimulatedERP())
    extraction = InvoiceExtraction(
        invoice_number="INV-42",
        vendor_name="Acme Supplies",
        currency="INR",
        total=1250.0,
        confidence=0.98,
    )
    workflow_result = workflow.run(
        task_id=task.task_id,
        action_id=uuid4(),
        extraction=extraction,
        idempotency_key="e2e-inv-42",
    )
    assert workflow_result.erp_result is not None
    assert workflow_result.erp_result.accepted is True
    assert workflow_result.external_id is not None

    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page()
        page.set_content(
            """
            <input data-autoworker-id="invoice-number" />
            <button data-autoworker-id="submit-invoice"
                    onclick="document.body.dataset.submitted='true'">Submit</button>
            """
        )
        session = PlaywrightBrowserSession(page)
        session.execute(
            BrowserAction(
                task_id=task.task_id,
                action_id=uuid4(),
                operation="fill",
                target=BrowserElement(element_id="invoice-number", role="textbox"),
                value="INV-42",
            )
        )
        session.execute(
            BrowserAction(
                task_id=task.task_id,
                action_id=uuid4(),
                operation="click",
                target=BrowserElement(element_id="submit-invoice", role="button"),
            )
        )
        assert page.locator('[data-autoworker-id="invoice-number"]').input_value() == "INV-42"
        assert page.locator("body").get_attribute("data-submitted") == "true"
        browser.close()

    with Session(engine) as session:
        repository = SqlAlchemyTaskRepository(session)
        repository.append_audit(
            AuditEvent(
                task_id=task.task_id,
                event_type="E2E_VERIFIED",
                actor="E2E",
                details={
                    "external_id": workflow_result.external_id,
                    "browser_invoice_number": "INV-42",
                    "erp_status": workflow_result.erp_result.record.status if workflow_result.erp_result.record else None,
                },
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyTaskRepository(session)
        stored_events = repository.list_audit(task.task_id)

    assert any(event.event_type == "E2E_VERIFIED" for event in stored_events)
