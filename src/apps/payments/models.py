"""
Payment Gateway Integration — Module 15 foundation.

Provider-agnostic payment orchestration: PaymentIntent/PaymentAttempt are a
validated state machine (CREATED -> PENDING -> AUTHORIZED/SUCCEEDED/FAILED/
CANCELLED/EXPIRED), separate from apps.finance.PaymentTransaction (a
post-hoc settlement ledger entry created only after a payment is already
known to have happened) and separate from apps.wallet (customer stored
value). Nothing here creates Wallet/WalletTransaction or
finance.PaymentTransaction rows — that wiring is deferred to a future
orchestration module.

payer_party reuses apps.finance.FinancialParty (the existing generic
financial-counterparty abstraction) rather than duplicating customer
ownership, mirroring apps.wallet.Wallet.party.

Money constants are intentionally duplicated (not imported) from
apps.finance.models.document to avoid a runtime dependency on apps.finance.
"""

import uuid

from django.db import models

from apps.common.managers import TenantScopedManager

MONEY_MAX_DIGITS = 14
MONEY_DECIMAL_PLACES = 2
DEFAULT_CURRENCY = "IRR"


class PaymentProvider(models.TextChoices):
    """Registered PSP adapters. Only FAKE exists today — real PSPs are deferred."""

    FAKE = "FAKE", "Fake (test/internal)"


class PaymentStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    PENDING = "PENDING", "Pending"
    AUTHORIZED = "AUTHORIZED", "Authorized"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


# Terminal statuses accept no further transitions.
TERMINAL_STATUSES = frozenset(
    {
        PaymentStatus.SUCCEEDED,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
        PaymentStatus.EXPIRED,
    }
)


class PaymentIntent(models.Model):
    """Represents an intent to collect a payment. Status is a validated state machine."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="payment_intents",
    )
    payer_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        related_name="payment_intents",
    )

    amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)
    provider = models.CharField(max_length=20, choices=PaymentProvider.choices, default=PaymentProvider.FAKE)
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.CREATED,
        db_index=True,
    )

    idempotency_key = models.CharField(max_length=255)

    reference_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Generic tag for what this payment is for, e.g. 'Order', 'Quote'. No FK — decoupled by design.",
    )
    reference_id = models.UUIDField(null=True, blank=True)

    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "payments_payment_intent"
        ordering = ["-created_at"]
        unique_together = [("tenant", "idempotency_key")]

    def __str__(self):
        return f"PaymentIntent({self.amount} {self.currency}) [{self.status}]"


class PaymentAttempt(models.Model):
    """One provider-facing attempt to collect a PaymentIntent. Status is a validated state machine."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="payment_attempts",
    )
    intent = models.ForeignKey(
        "payments.PaymentIntent",
        on_delete=models.PROTECT,
        related_name="attempts",
    )

    provider = models.CharField(max_length=20, choices=PaymentProvider.choices)
    provider_reference = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )

    request_snapshot = models.JSONField(default=dict, blank=True)
    response_snapshot = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "payments_payment_attempt"
        ordering = ["-created_at"]
        unique_together = [("tenant", "provider_reference")]

    def __str__(self):
        return f"PaymentAttempt({self.provider_reference}) [{self.status}]"


class PaymentCallback(models.Model):
    """Append-only log of every received provider callback, accepted or rejected."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="payment_callbacks",
    )
    attempt = models.ForeignKey(
        "payments.PaymentAttempt",
        on_delete=models.PROTECT,
        related_name="callbacks",
    )

    provider_event_id = models.CharField(
        max_length=255,
        help_text="Provider-supplied idempotency identifier for this callback.",
    )
    payload = models.JSONField(default=dict, blank=True)

    accepted = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True)
    resulting_status = models.CharField(max_length=20, choices=PaymentStatus.choices, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "payments_payment_callback"
        ordering = ["-created_at"]
        unique_together = [("attempt", "provider_event_id")]

    def __str__(self):
        return f"PaymentCallback({self.provider_event_id}) accepted={self.accepted}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("PaymentCallback is append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("PaymentCallback is append-only and cannot be deleted.")
