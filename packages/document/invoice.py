"""Invoice validation layer between OCR extraction and execution."""

from dataclasses import dataclass

from packages.tools.document import InvoiceExtraction


@dataclass(frozen=True)
class InvoiceValidationResult:
    valid: bool
    errors: tuple[str, ...] = ()


def validate_invoice(extraction: InvoiceExtraction) -> InvoiceValidationResult:
    errors: list[str] = []
    if not extraction.invoice_number:
        errors.append("invoice_number is required")
    if not extraction.vendor_name:
        errors.append("vendor_name is required")
    if not extraction.currency:
        errors.append("currency is required")
    if extraction.total is None or extraction.total <= 0:
        errors.append("total must be greater than zero")
    if extraction.confidence < 0.8:
        errors.append("extraction confidence is below 0.80")
    return InvoiceValidationResult(valid=not errors, errors=tuple(errors))
