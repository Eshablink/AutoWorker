from decimal import Decimal
from uuid import uuid4

import pytest

from packages.documents.contracts import DocumentExtraction, ExtractedField
from packages.documents.invoice import InvoiceData, parse_invoice


def test_parse_invoice_extraction():
    extraction = DocumentExtraction(
        document_id=uuid4(),
        fields=(
            ExtractedField("invoice_number", "INV-42", 0.99),
            ExtractedField("vendor_name", "Acme", 0.98),
            ExtractedField("total_amount", "1250.50", 0.97),
            ExtractedField("currency", "usd", 0.99),
        ),
    )
    result = parse_invoice(extraction)
    assert result.invoice_number == "INV-42"
    assert result.total_amount == Decimal("1250.50")
    assert result.currency == "USD"


def test_invoice_rejects_negative_total():
    with pytest.raises(ValueError):
        InvoiceData("INV-1", "Acme", Decimal("-1"), "USD")
