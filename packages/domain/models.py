"""AutoWorker Core Domain Contracts & Schemas.

Production-hardened Pydantic v2 schemas for tasks, actions, tools, policy decisions,
approvals, verification proofs, evidence artifacts, and audit events.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def default_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    RECOVERING = "RECOVERING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ActionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ToolRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PolicyOutcome(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class EvidenceReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    action_id: Optional[UUID] = None
    kind: str
    uri_or_path: str
    hash_checksum: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=default_utc_now)

    @field_validator("kind", "uri_or_path")
    @classmethod
    def validate_non_empty_string(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"Field '{info.field_name}' cannot be empty or whitespace.")
        return v.strip()


class ToolDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: str
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    risk_level: ToolRisk = ToolRisk.LOW
    is_side_effecting: bool = False
    requires_idempotency_key: bool = False
    timeout_seconds: int = Field(default=30, ge=1, le=300)

    @field_validator("tool_id", "name", "description")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"Tool definition field '{info.field_name}' cannot be empty.")
        return v.strip()


class PolicyDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    action_id: UUID
    tool_id: str
    outcome: PolicyOutcome
    risk_level: ToolRisk
    reason: str
    policy_version: str = "v1"
    evaluated_rules: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=default_utc_now)

    @field_validator("tool_id", "reason", "policy_version")
    @classmethod
    def validate_strings(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"Policy decision field '{info.field_name}' cannot be empty.")
        return v.strip()

    @model_validator(mode="after")
    def validate_high_risk_policy_outcome(self) -> "PolicyDecision":
        if self.risk_level in {ToolRisk.HIGH, ToolRisk.CRITICAL} and self.outcome == PolicyOutcome.ALLOW:
            raise ValueError(
                f"Policy violation: High-risk tool calls ({self.risk_level.value}) cannot be assigned 'ALLOW'. "
                "Outcome must be 'REQUIRE_APPROVAL' or 'DENY'."
            )
        return self


class ApprovalRequest(BaseModel):
    approval_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    action_id: UUID
    policy_decision_id: UUID
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_action_name: str
    tool_id: str
    payload_summary: Dict[str, Any]
    risk_level: ToolRisk
    reason_required: str
    approver_id: Optional[str] = None
    approval_comment: Optional[str] = None
    created_at: datetime = Field(default_factory=default_utc_now)
    decided_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    @field_validator("expires_at")
    @classmethod
    def normalize_expiry(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @property
    def expired(self) -> bool:
        return self.expires_at is not None and datetime.now(timezone.utc) >= self.expires_at

    @field_validator("requested_action_name", "tool_id", "reason_required")
    @classmethod
    def validate_required_text(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"ApprovalRequest field '{info.field_name}' cannot be empty.")
        return v.strip()


class VerificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    verification_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    action_id: Optional[UUID] = None
    success: bool
    verification_type: str
    query_or_check: str
    expected_state: Dict[str, Any]
    actual_state: Dict[str, Any]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    evidence_refs: List[EvidenceReference] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=default_utc_now)

    @field_validator("verification_type", "query_or_check")
    @classmethod
    def validate_non_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"VerificationResult field '{info.field_name}' cannot be empty.")
        return v.strip()


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    action_id: Optional[UUID] = None
    event_type: str
    actor: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=default_utc_now)

    @field_validator("event_type", "actor")
    @classmethod
    def validate_audit_strings(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"AuditEvent field '{info.field_name}' cannot be empty.")
        return v.strip()


class TaskAction(BaseModel):
    action_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    step_number: int = Field(..., ge=1)
    tool_id: str
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    tool_output: Optional[Dict[str, Any]] = None
    is_side_effecting: bool = False
    idempotency_key: Optional[str] = None
    status: ActionStatus = ActionStatus.PENDING
    decision_summary: str
    reason_code: Optional[str] = None
    observation: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    policy_decision: Optional[PolicyDecision] = None
    approval_request: Optional[ApprovalRequest] = None
    evidence_refs: List[EvidenceReference] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @field_validator("tool_id", "decision_summary")
    @classmethod
    def validate_action_text(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"TaskAction field '{info.field_name}' cannot be empty.")
        return v.strip()

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        normalized = v.strip()
        if not normalized:
            raise ValueError("idempotency_key cannot be empty or whitespace.")
        return normalized

    @model_validator(mode="after")
    def validate_retries(self) -> "TaskAction":
        if self.retry_count > self.max_retries:
            raise ValueError(f"retry_count ({self.retry_count}) cannot exceed max_retries ({self.max_retries}).")
        return self


class Task(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    version: int = Field(default=1, ge=1)
    goal: str = Field(..., min_length=5)
    status: TaskStatus = TaskStatus.CREATED
    context_memory: Dict[str, Any] = Field(default_factory=dict)
    actions: List[TaskAction] = Field(default_factory=list)
    current_step_index: int = Field(default=0, ge=0)
    error_message: Optional[str] = None
    verification_result: Optional[VerificationResult] = None
    created_at: datetime = Field(default_factory=default_utc_now)
    updated_at: datetime = Field(default_factory=default_utc_now)

    @field_validator("goal")
    @classmethod
    def validate_goal_not_blank(cls, v: str) -> str:
        normalized = v.strip()
        if len(normalized) < 5:
            raise ValueError("Task goal must contain at least 5 non-whitespace characters.")
        return normalized
