"""Deterministic document extractor for tests and local development."""

from packages.documents.contracts import DocumentArtifact, DocumentExtraction, ExtractedField


class MockDocumentExtractor:
    def extract(self, document: DocumentArtifact) -> DocumentExtraction:
        return DocumentExtraction(
            document_id=document.document_id,
            fields=(ExtractedField(name="document_type", value=document.media_type, confidence=1.0),),
            raw_text="",
        )
