"""Flagship invoice workflow composition boundary."""

from dataclasses import dataclass
from uuid import UUID

from packages.document.invoice import InvoiceValidationResult, validate_invoice
from packages.tools.document import InvoiceExtraction
from packages.tools.erp import ERPAdapter, ERPWriteRequest, ERPWriteResult


@dataclass(frozen=True)
class InvoiceWorkflowResult:
    validation: InvoiceValidationResult
    erp_result: ERPWriteResult | None
    external_id: str | None


class InvoiceWorkflow:
    def __init__(self, erp: ERPAdapter) -> None:
        self.erp = erp

    def run(
        self,
        *,
        task_id: UUID,
        action_id: UUID,
        extraction: InvoiceExtraction,
        idempotency_key: str,
    ) -> InvoiceWorkflowResult:
        validation = validate_invoice(extraction)
        if not validation.valid:
            return InvoiceWorkflowResult(validation, None, None)

        result = self.erp.create_invoice(
            ERPWriteRequest(
                task_id=task_id,
                action_id=action_id,
                invoice_number=extraction.invoice_number,
                vendor_name=extraction.vendor_name,
                currency=extraction.currency,
                total=extraction.total,
                idempotency_key=idempotency_key,
            )
        )
        return InvoiceWorkflowResult(
            validation=validation,
            erp_result=result,
            external_id=result.record.external_id if result.record else None,
        )
