from uuid import uuid4

from packages.integrations.simulated_erp import SimulatedERP
from packages.tools.document import InvoiceExtraction
from packages.workflows.invoice import InvoiceWorkflow


def test_invoice_workflow_posts_valid_invoice_and_returns_external_id():
    workflow = InvoiceWorkflow(SimulatedERP())
    result = workflow.run(
        task_id=uuid4(),
        action_id=uuid4(),
        extraction=InvoiceExtraction(
            invoice_number="INV-101",
            vendor_name="Acme",
            currency="USD",
            total=250.0,
            confidence=0.96,
        ),
        idempotency_key="invoice-101",
    )
    assert result.validation.valid
    assert result.erp_result.accepted
    assert result.external_id == "erp-000001"


def test_invoice_workflow_reuses_idempotency_key():
    workflow = InvoiceWorkflow(SimulatedERP())
    task_id, action_id = uuid4(), uuid4()
    extraction = InvoiceExtraction(
        invoice_number="INV-102",
        vendor_name="Acme",
        currency="EUR",
        total=90.0,
        confidence=0.95,
    )
    first = workflow.run(
        task_id=task_id,
        action_id=action_id,
        extraction=extraction,
        idempotency_key="invoice-102",
    )
    second = workflow.run(
        task_id=task_id,
        action_id=action_id,
        extraction=extraction,
        idempotency_key="invoice-102",
    )
    assert first.external_id == second.external_id


def test_invoice_workflow_stops_before_erp_for_invalid_extraction():
    workflow = InvoiceWorkflow(SimulatedERP())
    result = workflow.run(
        task_id=uuid4(),
        action_id=uuid4(),
        extraction=InvoiceExtraction(
            invoice_number=None,
            vendor_name="Acme",
            currency="USD",
            total=120.0,
            confidence=0.98,
        ),
        idempotency_key="bad-invoice",
    )
    assert result.validation.valid is False
    assert result.erp_result is None
