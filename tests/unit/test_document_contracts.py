from uuid import uuid4

import pytest

from packages.documents.contracts import DocumentArtifact, ExtractedField
from packages.documents.mock import MockDocumentExtractor


def test_mock_document_extraction():
    document = DocumentArtifact(
        task_id=uuid4(),
        filename="invoice.pdf",
        media_type="application/pdf",
        uri="file:///invoice.pdf",
    )
    result = MockDocumentExtractor().extract(document)
    assert result.document_id == document.document_id
    assert result.fields[0].name == "document_type"


def test_document_artifact_requires_filename():
    with pytest.raises(ValueError):
        DocumentArtifact(filename="", uri="file:///invoice.pdf")


def test_extracted_field_validates_confidence():
    with pytest.raises(ValueError):
        ExtractedField(name="total", value=100, confidence=1.5)
