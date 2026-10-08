import hashlib
import io
import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel

from apps.api.auth import Principal, require_api_auth
from apps.api.database import get_session_factory
from packages.persistence.sqlalchemy import DocumentRecord

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_api_auth)])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")


class DocumentResponse(BaseModel):
    document_id: UUID
    filename: str
    media_type: str
    size_bytes: int
    sha256: str
    extracted_text_preview: str
    created_at: datetime


def _safe_filename(name: str | None) -> str:
    cleaned = _FILENAME_RE.sub("_", (name or "document").replace("\\", "/").split("/")[-1]).strip()
    return (cleaned or "document")[:255]


def _extract_text(filename: str, media_type: str, content: bytes) -> str:
    if media_type in {"text/plain", "text/markdown"}:
        return content.decode("utf-8", errors="replace")[:200_000]
    if media_type == "application/pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            return "\n".join((page.extract_text() or "") for page in reader.pages)[:200_000]
        except Exception:
            return ""
    if media_type.endswith("wordprocessingml.document"):
        try:
            from docx import Document
            document = Document(io.BytesIO(content))
            return "\n".join(p.text for p in document.paragraphs)[:200_000]
        except Exception:
            return ""
    return ""


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile, principal: Principal = Depends(require_api_auth)) -> DocumentResponse:
    if principal.role == "operator":
        raise HTTPException(status_code=403, detail="Operator tokens cannot own user documents.")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Supported formats: PDF, TXT, Markdown, and DOCX.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the 10 MB upload limit.")
    if not content:
        raise HTTPException(status_code=400, detail="Document is empty.")

    filename = _safe_filename(file.filename)
    digest = hashlib.sha256(content).hexdigest()
    extracted = _extract_text(filename, file.content_type, content)
    document = DocumentRecord(
        document_id=str(uuid4()),
        user_id=str(principal.user_id),
        filename=filename,
        media_type=file.content_type,
        size_bytes=len(content),
        sha256=digest,
        content=content,
        extracted_text=extracted,
        created_at=datetime.now(timezone.utc),
    )
    session = get_session_factory()()
    try:
        session.add(document)
        session.commit()
        return DocumentResponse(
            document_id=UUID(document.document_id),
            filename=document.filename,
            media_type=document.media_type,
            size_bytes=document.size_bytes,
            sha256=document.sha256,
            extracted_text_preview=document.extracted_text[:1000],
            created_at=document.created_at,
        )
    finally:
        session.close()


@router.get("", response_model=list[DocumentResponse])
def list_documents(principal: Principal = Depends(require_api_auth)) -> list[DocumentResponse]:
    session = get_session_factory()()
    try:
        rows = session.query(DocumentRecord).filter(
            DocumentRecord.user_id == str(principal.user_id)
        ).order_by(DocumentRecord.created_at.desc()).limit(100).all()
        return [
            DocumentResponse(
                document_id=UUID(row.document_id),
                filename=row.filename,
                media_type=row.media_type,
                size_bytes=row.size_bytes,
                sha256=row.sha256,
                extracted_text_preview=row.extracted_text[:1000],
                created_at=row.created_at,
            )
            for row in rows
        ]
    finally:
        session.close()


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: UUID, principal: Principal = Depends(require_api_auth)) -> DocumentResponse:
    session = get_session_factory()()
    try:
        row = session.query(DocumentRecord).filter(
            DocumentRecord.document_id == str(document_id),
            DocumentRecord.user_id == str(principal.user_id),
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        return DocumentResponse(
            document_id=document_id,
            filename=row.filename,
            media_type=row.media_type,
            size_bytes=row.size_bytes,
            sha256=row.sha256,
            extracted_text_preview=row.extracted_text[:1000],
            created_at=row.created_at,
        )
    finally:
        session.close()


@router.get("/{document_id}/content")
def download_document(document_id: UUID, principal: Principal = Depends(require_api_auth)) -> Response:
    session = get_session_factory()()
    try:
        row = session.query(DocumentRecord).filter(
            DocumentRecord.document_id == str(document_id),
            DocumentRecord.user_id == str(principal.user_id),
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        return Response(
            content=row.content,
            media_type=row.media_type,
            headers={"Content-Disposition": f'attachment; filename="{row.filename}"'},
        )
    finally:
        session.close()
