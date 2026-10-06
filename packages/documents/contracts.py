"""Typed document/OCR contracts independent of a vendor implementation."""

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DocumentArtifact:
    document_id: UUID = field(default_factory=uuid4)
    task_id: UUID | None = None
    filename: str = ""
    media_type: str = "application/octet-stream"
    uri: str = ""
    sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.filename.strip():
            raise ValueError("Document filename is required.")
        if not self.uri.strip():
            raise ValueError("Document URI is required.")


@dataclass(frozen=True)
class ExtractedField:
    name: str
    value: Any
    confidence: float

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Extracted field name is required.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Extracted field confidence must be between 0 and 1.")


@dataclass(frozen=True)
class DocumentExtraction:
    document_id: UUID
    fields: tuple[ExtractedField, ...]
    raw_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class DocumentExtractor(Protocol):
    def extract(self, document: DocumentArtifact) -> DocumentExtraction:
        ...


class OCRProvider(Protocol):
    def extract_text(self, document: DocumentArtifact) -> str:
        ...
