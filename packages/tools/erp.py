"""Controlled ERP adapter contracts with explicit verification hooks."""

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class ERPInvoice:
    external_id: str
    invoice_number: str
    vendor_name: str
    currency: str
    total: float
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ERPWriteRequest:
    task_id: UUID
    action_id: UUID
    invoice_number: str
    vendor_name: str
    currency: str
    total: float
    idempotency_key: str


@dataclass(frozen=True)
class ERPWriteResult:
    accepted: bool
    record: ERPInvoice | None
    validation_errors: tuple[str, ...] = ()


class ERPAdapter(Protocol):
    def create_invoice(self, request: ERPWriteRequest) -> ERPWriteResult:
        ...

    def get_invoice(self, external_id: str) -> ERPInvoice | None:
        ...
