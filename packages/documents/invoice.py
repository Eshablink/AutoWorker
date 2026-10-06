"""Invoice extraction schema used by the flagship AutoWorker workflow."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from packages.documents.contracts import DocumentExtraction


@dataclass(frozen=True)
class InvoiceData:
    invoice_number: str
    vendor_name: str
    total_amount: Decimal
    currency: str
    due_date: str | None = None

    def __post_init__(self) -> None:
        if not self.invoice_number.strip():
            raise ValueError("Invoice number is required.")
        if not self.vendor_name.strip():
            raise ValueError("Vendor name is required.")
        if self.total_amount < 0:
            raise ValueError("Invoice total cannot be negative.")
        if len(self.currency.strip()) != 3:
            raise ValueError("Invoice currency must be a 3-letter code.")


def parse_invoice(extraction: DocumentExtraction) -> InvoiceData:
    values = {field.name: field.value for field in extraction.fields}
    try:
        return InvoiceData(
            invoice_number=str(values["invoice_number"]),
            vendor_name=str(values["vendor_name"]),
            total_amount=Decimal(str(values["total_amount"])),
            currency=str(values["currency"]).upper(),
            due_date=str(values["due_date"]) if values.get("due_date") is not None else None,
        )
    except KeyError as exc:
        raise ValueError(f"Missing required invoice field: {exc.args[0]}") from exc
