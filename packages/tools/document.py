"""Document ingestion and extraction contracts."""

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID


class DocumentToolError(RuntimeError):
    """Base error for document pipeline failures."""


@dataclass(frozen=True)
class DocumentArtifact:
    document_id: UUID
    media_type: str
    uri: str
    sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.media_type.strip():
            raise ValueError("Document media_type cannot be empty.")
        if not self.uri.strip():
            raise ValueError("Document URI cannot be empty.")


@dataclass(frozen=True)
class OCRResult:
    text: str
    confidence: float
    pages: int
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("OCR confidence must be between 0 and 1.")
        if self.pages < 1:
            raise ValueError("OCR page count must be at least 1.")


@dataclass(frozen=True)
class InvoiceExtraction:
    invoice_number: str | None
    vendor_name: str | None
    invoice_date: str | None
    currency: str | None
    subtotal: float | None
    tax: float | None
    total: float | None
    line_items: tuple[dict[str, Any], ...] = ()
    confidence: float = 0.0
    source_document_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.invoice_number is not None and not self.invoice_number.strip():
            raise ValueError("invoice_number cannot be blank.")
        if self.vendor_name is not None and not self.vendor_name.strip():
            raise ValueError("vendor_name cannot be blank.")
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Invoice extraction confidence must be between 0 and 1.")


class OCRAdapter(Protocol):
    def extract_text(self, document: DocumentArtifact, *, timeout_seconds: int = 60) -> OCRResult:
        ...


class InvoiceExtractor(Protocol):
    def extract_invoice(self, document: DocumentArtifact, ocr: OCRResult) -> InvoiceExtraction:
        ...
