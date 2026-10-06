"""Deterministic in-memory ERP used only for tests and the local demo."""

from packages.tools.erp import ERPAdapter, ERPInvoice, ERPWriteRequest, ERPWriteResult


class SimulatedERP:
    def __init__(self) -> None:
        self._records: dict[str, ERPInvoice] = {}

    def create_invoice(self, request: ERPWriteRequest) -> ERPWriteResult:
        if request.idempotency_key in self._records:
            return ERPWriteResult(accepted=True, record=self._records[request.idempotency_key])

        if request.total <= 0:
            return ERPWriteResult(accepted=False, record=None, validation_errors=("total must be positive",))
        if request.currency not in {"USD", "EUR", "INR", "GBP"}:
            return ERPWriteResult(
                accepted=False,
                record=None,
                validation_errors=("unsupported currency",),
            )

        record = ERPInvoice(
            external_id=f"erp-{len(self._records) + 1:06d}",
            invoice_number=request.invoice_number,
            vendor_name=request.vendor_name,
            currency=request.currency,
            total=request.total,
            status="POSTED",
        )
        self._records[request.idempotency_key] = record
        return ERPWriteResult(accepted=True, record=record)

    def get_invoice(self, external_id: str) -> ERPInvoice | None:
        return next(
            (record for record in self._records.values() if record.external_id == external_id),
            None,
        )
