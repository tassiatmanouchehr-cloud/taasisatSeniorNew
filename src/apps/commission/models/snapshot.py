"""
CommissionSnapshot — Financial Core PR-A.

The immutable freeze of "which commission policy applies to this order",
captured once at proposal/offer acceptance (see
apps.booking.services.assignment_service.AssignmentService.assign(), the
smallest correct integration point identified by inspecting the existing
accepted-proposal representation — see docs/architecture/adr/
ADR-2026-XX-financial-core-foundation.md).

Every later financial document (invoice, extra invoice, escrow record,
allocation, settlement, statement, report, dispute, refund) for this order
must read this snapshot rather than re-resolving current configuration —
that is the entire point of freezing it. PR-A only creates and stores the
snapshot; nothing in PR-A yet consumes it for real settlement math (that is
PR-C's scope per the roadmap) — see CommissionSnapshot's own docstring
note below and the PR-A final report's "known limitations" section.

Deliberately carries no gross amount requirement: apps.orders.Order has no
price/amount field at assignment time (pricing resolves later, at invoice
time, via apps.pricing/apps.finance) — accepted_gross_amount is therefore
nullable here and populated by a later PR once the Quote-to-Order pricing
bridge is designed. This is a known, explicitly-documented PR-A limitation,
not a silent omission.
"""

import uuid

from django.db import models

from apps.common.managers import TenantScopedManager

DEFAULT_CURRENCY = "IRR"


class PolicySource(models.TextChoices):
    """Which tier of the four-tier priority chain produced this snapshot's rates."""

    CONTRACT = "CONTRACT", "Active Company-Caregiver Contract"
    PLATFORM_OVERRIDE = "PLATFORM_OVERRIDE", "Platform-Specific Override"
    COOPERATION_DEFAULT = "COOPERATION_DEFAULT", "Cooperation-Type Default"
    GLOBAL_DEFAULT = "GLOBAL_DEFAULT", "Global Default"


class CalculationBase(models.TextChoices):
    CUSTOMER_PAID_AMOUNT = "CUSTOMER_PAID_AMOUNT", "Customer-Paid Amount"


ROUNDING_POLICY_INTEGER_RESIDUAL_TO_CAREGIVER = "INTEGER_IRR_FLOOR_RESIDUAL_TO_CAREGIVER"


class CommissionSnapshot(models.Model):
    """Immutable, per-order freeze of the resolved commission policy."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="commission_snapshots",
    )

    # A ForeignKey, not OneToOne: an order that is reassigned after a
    # payment-deadline expiry (Business Model Section 2 — "all previous
    # offers expire... order becomes available for new offers") starts a
    # genuinely new acceptance cycle and must get its own fresh snapshot
    # reflecting the newly-assigned supplier, never the expired cycle's
    # frozen policy. See CommissionSnapshotService.create_snapshot_for_order
    # for how "the current snapshot for this order" is resolved.
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="commission_snapshots",
    )
    supplier = models.ForeignKey(
        "kernel.ServiceSupplier",
        on_delete=models.PROTECT,
        related_name="commission_snapshots",
    )

    cooperation_type = models.CharField(max_length=20)

    policy_source = models.CharField(max_length=30, choices=PolicySource.choices)
    contract = models.ForeignKey(
        "commission.CommissionContract",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="snapshots",
    )
    policy_version_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="apps.kernel.models.policy.PolicyVersion.id this snapshot was resolved from, when policy_source is not CONTRACT.",
    )

    # Service-line shares (percent of the platform's non-goods commission base).
    platform_rate_percent = models.PositiveSmallIntegerField()
    company_rate_percent = models.PositiveSmallIntegerField(default=0)
    caregiver_rate_percent = models.PositiveSmallIntegerField()

    # Goods-line shares, resolved independently (Business Model Section 16 / Goods Policy).
    goods_platform_rate_percent = models.PositiveSmallIntegerField()
    goods_company_rate_percent = models.PositiveSmallIntegerField(default=0)
    goods_caregiver_rate_percent = models.PositiveSmallIntegerField()

    company_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="commission_snapshots_as_company",
    )
    caregiver_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="commission_snapshots_as_caregiver",
    )

    calculation_base = models.CharField(
        max_length=30,
        choices=CalculationBase.choices,
        default=CalculationBase.CUSTOMER_PAID_AMOUNT,
    )
    currency = models.CharField(max_length=10, default=DEFAULT_CURRENCY)
    rounding_policy = models.CharField(max_length=60, default=ROUNDING_POLICY_INTEGER_RESIDUAL_TO_CAREGIVER)

    accepted_gross_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Null in PR-A — apps.orders.Order carries no price at assignment time yet.",
    )
    discount_funding_policy = models.CharField(max_length=30, default="PLATFORM_FUNDED")
    gateway_fee_policy = models.CharField(max_length=30, default="PLATFORM_ABSORBED")

    effective_timestamp = models.DateTimeField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "commission_snapshot"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "order"], name="idx_commsnap_tenant_order"),
        ]

    def __str__(self):
        return f"CommissionSnapshot(order={self.order_id}) [{self.policy_source}]"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("CommissionSnapshot is immutable and cannot be modified after creation.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("CommissionSnapshot cannot be deleted.")
