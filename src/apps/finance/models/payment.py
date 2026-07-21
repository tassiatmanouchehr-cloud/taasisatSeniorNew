"""PaymentTransaction — Module 05 foundation. Internal record only; no gateway integration."""

import uuid

from django.db import models
from django.db.models import Q

from apps.common.managers import TenantScopedManager

from .document import DEFAULT_CURRENCY, MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS


class PaymentMethod(models.TextChoices):
    ONLINE = "ONLINE", "Online"
    CASH = "CASH", "Cash"
    CARD_TO_CARD = "CARD_TO_CARD", "Card to Card"
    WALLET = "WALLET", "Wallet"
    MANUAL = "MANUAL", "Manual"


class PaymentStatus(models.TextChoices):
    INITIATED = "INITIATED", "Initiated"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    REFUNDED = "REFUNDED", "Refunded"


class PaymentTransaction(models.Model):
    """An internal record of money movement. Never deleted, never a real gateway call."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="payment_transactions",
    )
    source_document = models.ForeignKey(
        "finance.FinancialDocument",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    obligation = models.ForeignKey(
        "finance.FinancialObligation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    payer_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        related_name="payments_made",
    )
    receiver_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        related_name="payments_received",
    )

    amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.INITIATED,
        db_index=True,
    )

    provider_reference = models.CharField(max_length=255, blank=True)
    collected_by_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="collected_payments",
    )
    occurred_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "finance_payment_transaction"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"], name="idx_finpay_tenant_status"),
        ]
        constraints = [
            # Database-level backstop (Epic 03 Sprint 1 remediation) against a
            # concurrent double-settlement race: two overlapping callers both
            # passing a service-layer "does a SUCCEEDED payment already exist
            # for this provider_reference" check before either commits. Scoped
            # to non-blank provider_reference only — CASH/MANUAL payments that
            # never set one are unaffected and may still repeat blank values.
            models.UniqueConstraint(
                fields=["tenant", "provider_reference"],
                condition=Q(provider_reference__gt=""),
                name="uq_payment_transaction_tenant_provider_reference",
            ),
        ]

    def __str__(self):
        return f"Payment {self.id}: {self.amount} {self.currency} [{self.status}]"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("PaymentTransaction is append-only and cannot be modified after creation.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("PaymentTransaction cannot be deleted.")
