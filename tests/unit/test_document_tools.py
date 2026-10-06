from uuid import uuid4

from packages.tools.document import DocumentArtifact, InvoiceExtraction, OCRResult


def test_document_contracts_capture_provenance():
    document_id = uuid4()
    artifact = DocumentArtifact(
        document_id=document_id,
        media_type="application/pdf",
        uri="s3://autoworker/invoices/INV-101.pdf",
        sha256="a" * 64,
    )
    ocr = OCRResult(text="Invoice INV-101 Total 100.00", confidence=0.98, pages=1)

    assert artifact.document_id == document_id
    assert artifact.sha256 is not None
    assert ocr.confidence == 0.98


def test_invoice_extraction_keeps_source_document():
    document_id = uuid4()
    extraction = InvoiceExtraction(
        invoice_number="INV-101",
        vendor_name="Acme",
        total=100.0,
        confidence=0.97,
        source_document_id=document_id,
    )
    assert extraction.source_document_id == document_id
    assert extraction.total == 100.0
