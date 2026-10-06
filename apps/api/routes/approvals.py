from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from packages.domain.models import ApprovalStatus

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalDecision(BaseModel):
    status: ApprovalStatus
    comment: str | None = None


@router.post("/{approval_id}")
def decide_approval(approval_id: UUID, decision: ApprovalDecision):
    if decision.status not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
        raise HTTPException(status_code=400, detail="Approval must be APPROVED or REJECTED.")
    return {"approval_id": str(approval_id), "status": decision.status, "comment": decision.comment}
