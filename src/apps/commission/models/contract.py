"""
CommissionContract — Financial Core PR-A.

A bilateral, versioned commercial agreement between one Company
(FinancialPartyType.ORGANIZATION) and one Company-Affiliated Caregiver
(FinancialPartyType.SUPPLIER, cooperation_type=AFFILIATED) governing how the
non-platform 93% (100% - platform's frozen 7%) is split between them.

This is deliberately a dedicated model rather than another
apps.kernel.PolicyDefinition/PolicyVersion row: a contract has a two-party
proposer/approver negotiation shape (company proposes -> caregiver must
approve) and terminal REJECTED/TERMINATED states that PolicyVersion's
simpler draft/pending_approval/active/superseded lifecycle does not carry.
Platform-controlled tiers (per-caregiver override, per-cooperation-type
default, global default) are still resolved via apps.kernel.PolicyService —
see services/resolver_service.py for the full four-tier priority chain.

An organization administrator may only ever set company_share_percent /
caregiver_share_percent here — this model has no field an org admin could
use to touch the platform's share, by construction (see
services/contract_service.py for the enforcement of that rule; there is no
platform_share_percent write path exposed to org-admin-facing code at all).
"""

import uuid

from django.conf import settings
from django.db import models

from apps.common.managers import TenantScopedManager


class CommissionContractStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING_CAREGIVER_APPROVAL = "PENDING_CAREGIVER_APPROVAL", "Pending Caregiver Approval"
    ACTIVE = "ACTIVE", "Active"
    REJECTED = "REJECTED", "Rejected"
    SUPERSEDED = "SUPERSEDED", "Superseded"
    EXPIRED = "EXPIRED", "Expired"
    TERMINATED = "TERMINATED", "Terminated"


OPEN_CONTRACT_STATUSES = (
    CommissionContractStatus.DRAFT,
    CommissionContractStatus.PENDING_CAREGIVER_APPROVAL,
)


class CommissionContract(models.Model):
    """One versioned (company, caregiver) commission-split agreement."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="commission_contracts",
    )

    company_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        related_name="commission_contracts_as_company",
    )
    caregiver_party = models.ForeignKey(
        "finance.FinancialParty",
        on_delete=models.PROTECT,
        related_name="commission_contracts_as_caregiver",
    )

    status = models.CharField(
        max_length=30,
        choices=CommissionContractStatus.choices,
        default=CommissionContractStatus.DRAFT,
        db_index=True,
    )

    # The platform share is never editable through this model — it is
    # copied here only as a frozen reference for display/audit, resolved at
    # proposal time from the same PolicyService chain the resolver uses for
    # tier 2-4 (see CommissionContractService.propose()).
    platform_share_percent = models.PositiveSmallIntegerField()
    company_share_percent = models.PositiveSmallIntegerField()
    caregiver_share_percent = models.PositiveSmallIntegerField()

    effective_start = models.DateTimeField(null=True, blank=True)
    effective_end = models.DateTimeField(null=True, blank=True)

    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commission_contracts_proposed",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commission_contracts_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    reason = models.TextField(blank=True)

    version = models.PositiveIntegerField(default=1)
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="superseded_by_contract",
    )

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "commission_contract"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "caregiver_party", "status"], name="idx_commcontract_caregiver_st"),
            models.Index(fields=["tenant", "company_party", "status"], name="idx_commcontract_company_st"),
        ]

    def __str__(self):
        return (
            f"CommissionContract({self.company_party_id} x {self.caregiver_party_id}) v{self.version} [{self.status}]"
        )

    def clean_total(self):
        total = self.platform_share_percent + self.company_share_percent + self.caregiver_share_percent
        if total != 100:
            raise ValueError(f"CommissionContract shares must sum to exactly 100, got {total}.")
