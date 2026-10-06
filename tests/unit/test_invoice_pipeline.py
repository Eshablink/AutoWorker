from uuid import uuid4

from packages.document.invoice import validate_invoice
from packages.tools.document import InvoiceExtraction


def test_valid_invoice_passes_validation():
    result = validate_invoice(
        InvoiceExtraction(
            invoice_number="INV-101",
            vendor_name="Acme",
            invoice_date="2026-10-01",
            currency="USD",
            subtotal=100.0,
            tax=18.0,
            total=118.0,
            confidence=0.97,
            source_document_id=uuid4(),
        )
    )
    assert result.valid is True
    assert result.errors == ()


def test_low_confidence_invoice_is_rejected():
    result = validate_invoice(
        InvoiceExtraction(
            invoice_number="INV-101",
            vendor_name="Acme",
            currency="USD",
            total=118.0,
            confidence=0.55,
        )
    )
    assert result.valid is False
    assert "extraction confidence is below 0.80" in result.errors
