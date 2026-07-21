"""
Matching Engine models — Module 02 foundation (Sprint 4A).

MatchRound: one matching execution against an Order.
MatchCandidate: one ServiceSupplier evaluated within a MatchRound.

Matching only proposes candidates — it never writes Order.assigned_supplier.
See docs/adr/ADR-002_MATCHING_ENGINE.md for the full architecture decision.
"""

import uuid

from django.conf import settings
from django.db import models

from apps.common.managers import TenantScopedManager


class MatchRoundStatus(models.TextChoices):
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class MatchRound(models.Model):
    """One matching execution cycle for a single Order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="match_rounds",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="match_rounds",
    )
    status = models.CharField(
        max_length=20,
        choices=MatchRoundStatus.choices,
        default=MatchRoundStatus.RUNNING,
        db_index=True,
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    config_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of matching configuration at run time (immune to later config changes).",
    )
    failure_reason = models.TextField(blank=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "matching_round"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["tenant", "order", "status"], name="idx_matchround_tenant_order_st"),
        ]

    def __str__(self):
        return f"MatchRound({self.order_id}) [{self.status}]"


class EligibilityCode(models.TextChoices):
    """Structured eligibility outcome codes — never free text only."""

    ELIGIBLE = "eligible", "Eligible"
    WRONG_TENANT = "wrong_tenant", "Wrong Tenant"
    SUPPLIER_NOT_ACTIVE = "supplier_not_active", "Supplier Not Active"
    SUPPLIER_UNAVAILABLE = "supplier_unavailable", "Supplier Unavailable"
    CATEGORY_NOT_SUPPORTED = "category_not_supported", "Category Not Supported"
    SUPPLIER_TYPE_NOT_ALLOWED = "supplier_type_not_allowed", "Supplier Type Not Allowed by Marketplace Model"
    BELOW_VERIFICATION_THRESHOLD = "below_verification_threshold", "Below Minimum Verification Level"


class MatchCandidateStatus(models.TextChoices):
    GENERATED = "generated", "Generated"
    RANKED = "ranked", "Ranked"
    PRESENTED = "presented", "Presented"
    SELECTED = "selected", "Selected"
    REJECTED = "rejected", "Rejected"


class MatchCandidate(models.Model):
    """One ServiceSupplier evaluated (and possibly ranked) within a MatchRound."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="match_candidates",
    )
    match_round = models.ForeignKey(
        MatchRound,
        on_delete=models.CASCADE,
        related_name="candidates",
    )
    supplier = models.ForeignKey(
        "kernel.ServiceSupplier",
        on_delete=models.CASCADE,
        related_name="match_candidacies",
    )

    eligible = models.BooleanField(default=False)
    eligibility_code = models.CharField(max_length=40, choices=EligibilityCode.choices)
    eligibility_reason = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured explanation for the eligibility_code (ADR-02-07: explainable eligibility).",
    )

    rank_score = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    score_breakdown = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-component contributions to rank_score, for transparency/debugging.",
    )
    rank_position = models.IntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=MatchCandidateStatus.choices,
        default=MatchCandidateStatus.GENERATED,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "matching_candidate"
        ordering = ["rank_position", "-rank_score"]
        unique_together = [("match_round", "supplier")]
        indexes = [
            models.Index(fields=["tenant", "match_round", "eligible"], name="idx_mcand_tenant_round_elig"),
        ]

    def __str__(self):
        return f"MatchCandidate({self.supplier_id}) [{self.status}]"
