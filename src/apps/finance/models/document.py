"""
FinancialDocument — Module 05 foundation.

The base commercial document (invoice, credit note, debit note, refund
note, manual adjustment) — not just "invoice". Every downstream financial
record (obligation, payment, ledger entry) traces back to a document.

FinancialDocument is created strictly from a CLOSED ExecutionSession via
apps.finance.services.document_service.FinancialDocumentService — it never
mutates ExecutionSession or Order.
"""

import uuid
from decimal import Decimal

from django.db import models

from apps.common.managers import TenantScopedManager

MONEY_MAX_DIGITS = 14
MONEY_DECIMAL_PLACES = 2
DEFAULT_CURRENCY = "IRR"


class FinancialDocumentType(models.TextChoices):
    INVOICE = "INVOICE", "Invoice"
    SUPPLEMENTAL_INVOICE = "SUPPLEMENTAL_INVOICE", "Supplemental Invoice"
    CREDIT_NOTE = "CREDIT_NOTE", "Credit Note"
    DEBIT_NOTE = "DEBIT_NOTE", "Debit Note"
    REFUND_NOTE = "REFUND_NOTE", "Refund Note"
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT", "Manual Adjustment"


class FinancialDocumentStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ISSUED = "ISSUED", "Issued"
    LOCKED = "LOCKED", "Locked"
    CANCELLED = "CANCELLED", "Cancelled"
    VOIDED = "VOIDED", "Voided"
    PAID = "PAID", "Paid"
    PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
    DISPUTED = "DISPUTED", "Disputed"


LOCKED_STATUSES = (
    FinancialDocumentStatus.LOCKED,
    FinancialDocumentStatus.ISSUED,
    FinancialDocumentStatus.PAID,
    FinancialDocumentStatus.PARTIALLY_PAID,
    FinancialDocumentStatus.CANCELLED,
    FinancialDocumentStatus.VOIDED,
)

# Fields still allowed to change via save(update_fields=...) once a document
# has left DRAFT — lifecycle progression only, never financial content.
_MUTABLE_FIELDS_AFTER_DRAFT = frozenset({"status", "issued_at", "locked_at", "paid_at", "updated_at"})


class FinancialDocumentItemType(models.TextChoices):
    SERVICE = "SERVICE", "Service"
    TRAVEL = "TRAVEL", "Travel"
    GOODS = "GOODS", "Goods"
    EXTRA_SERVICE = "EXTRA_SERVICE", "Extra Service"
    OVERTIME = "OVERTIME", "Overtime"
    DISCOUNT = "DISCOUNT", "Discount"
    TAX = "TAX", "Tax"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"


class FinancialDocument(models.Model):
    """The base commercial document for the finance module."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="financial_documents",
    )

    document_type = models.CharField(max_length=30, choices=FinancialDocumentType.choices, db_index=True)

    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="financial_documents",
    )
    execution_session = models.ForeignKey(
        "execution.ExecutionSession", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="financial_documents",
    )

    issuer_party = models.ForeignKey(
        "finance.FinancialParty", on_delete=models.PROTECT, related_name="issued_documents",
    )
    payer_party = models.ForeignKey(
        "finance.FinancialParty", on_delete=models.PROTECT, related_name="payable_documents",
    )
    beneficiary_party = models.ForeignKey(
        "finance.FinancialParty", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="beneficiary_documents",
    )

    status = models.CharField(
        max_length=20, choices=FinancialDocumentStatus.choices,
        default=FinancialDocumentStatus.DRAFT, db_index=True,
    )

    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)
    subtotal_amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=Decimal("0"))
    discount_amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=Decimal("0"))
    tax_amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=Decimal("0"))

    pricing_snapshot = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    issued_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "finance_financial_document"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "document_type", "status"], name="idx_findoc_tenant_type_st"),
            models.Index(fields=["tenant", "execution_session"], name="idx_findoc_tenant_execsess"),
        ]

    def __str__(self):
        return f"{self.document_type} {self.id} [{self.status}]"

    @property
    def is_locked_for_edits(self) -> bool:
        return self.status in LOCKED_STATUSES

    def save(self, *args, **kwargs):
        """
        Once a document has left DRAFT (issued, locked, or beyond), only the
        lifecycle bookkeeping fields may still change (status progression and
        its timestamps) — never the financial content. Content corrections
        must happen through a CREDIT_NOTE/DEBIT_NOTE/REFUND_NOTE/
        MANUAL_ADJUSTMENT document instead.
        """
        if not self._state.adding and self.status != FinancialDocumentStatus.DRAFT:
            update_fields = kwargs.get("update_fields")
            if not update_fields or not set(update_fields) <= _MUTABLE_FIELDS_AFTER_DRAFT:
                raise ValueError(
                    "FinancialDocument is locked for edits once issued or locked; only "
                    f"{sorted(_MUTABLE_FIELDS_AFTER_DRAFT)} may be updated via update_fields. "
                    "Use a CREDIT_NOTE/DEBIT_NOTE/REFUND_NOTE/MANUAL_ADJUSTMENT document instead.",
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status != FinancialDocumentStatus.DRAFT:
            raise ValueError("FinancialDocument cannot be deleted once issued or locked.")
        super().delete(*args, **kwargs)


class FinancialDocumentItem(models.Model):
    """A single priced line on a FinancialDocument."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="financial_document_items",
    )
    document = models.ForeignKey(
        "finance.FinancialDocument", on_delete=models.CASCADE, related_name="items",
    )

    item_type = models.CharField(max_length=20, choices=FinancialDocumentItemType.choices)
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1"))
    unit_price = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    total_amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "finance_financial_document_item"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.item_type}: {self.description} ({self.total_amount})"
