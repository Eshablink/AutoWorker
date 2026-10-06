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


@dataclass(frozen=True)
class OCRResult:
    text: str
    confidence: float
    pages: int
    evidence_refs: tuple[str, ...] = ()


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


class OCRAdapter(Protocol):
    def extract_text(self, document: DocumentArtifact, *, timeout_seconds: int = 60) -> OCRResult:
        ...


class InvoiceExtractor(Protocol):
    def extract_invoice(self, document: DocumentArtifact, ocr: OCRResult) -> InvoiceExtraction:
        ...
