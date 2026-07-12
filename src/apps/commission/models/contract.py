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
    # Reserved/unimplemented in PR-A (System Architect Review of PR #44,
    # Remediation 8, documenting rather than closing this gap): no code
    # path ever transitions a contract to EXPIRED today — CommissionContract
    # has no proposal-response deadline of its own (unlike PaymentDeadline).
    # A future PR may add "an unapproved proposal auto-expires after N
    # days" and use this value then; until it does, EXPIRED must not be
    # treated as reachable by any caller.
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
        constraints = [
            # Remediation 2 (System Architect Review of PR #44): at most one
            # OPEN (DRAFT/PENDING_CAREGIVER_APPROVAL) proposal per
            # (tenant, company_party, caregiver_party) at a time — the real
            # DB-level safety net behind CommissionContractService
            # ._reject_any_open_proposal()'s pre-check, which only catches
            # the common case and cannot, on its own, close a genuine
            # concurrent-INSERT race.
            models.UniqueConstraint(
                fields=["tenant", "company_party", "caregiver_party"],
                condition=models.Q(status__in=list(OPEN_CONTRACT_STATUSES)),
                name="uq_commcontract_open_pair",
            ),
            # At most one ACTIVE contract per pair at a time — the DB-level
            # backstop behind CommissionContractService.approve()'s
            # select_for_update()+supersede-every-active-row transaction.
            models.UniqueConstraint(
                fields=["tenant", "company_party", "caregiver_party"],
                condition=models.Q(status="ACTIVE"),
                name="uq_commcontract_active_pair",
            ),
            # Remediation 3: every share must be within [0, 100] and the
            # three shares must sum to exactly 100 — enforced at the
            # database level, not only in CommissionContractService.propose()
            # (clean_total() above is intentionally NOT the enforcement
            # mechanism; see that method's docstring).
            models.CheckConstraint(
                check=(
                    models.Q(platform_share_percent__gte=0)
                    & models.Q(platform_share_percent__lte=100)
                    & models.Q(company_share_percent__gte=0)
                    & models.Q(company_share_percent__lte=100)
                    & models.Q(caregiver_share_percent__gte=0)
                    & models.Q(caregiver_share_percent__lte=100)
                ),
                name="chk_commcontract_share_range",
            ),
            models.CheckConstraint(
                check=models.Q(
                    platform_share_percent=100 - models.F("company_share_percent") - models.F("caregiver_share_percent")
                ),
                name="chk_commcontract_shares_sum100",
            ),
        ]

    def __str__(self):
        return (
            f"CommissionContract({self.company_party_id} x {self.caregiver_party_id}) v{self.version} [{self.status}]"
        )

    def clean_total(self):
        """Documented as unused dead code (System Architect Review of PR #44,
        Remediation 8): no caller invokes this — CommissionContractService
        .propose() validates the sum inline before create(), and
        chk_commcontract_shares_sum100 (see Meta.constraints above) is the
        real, unconditional database-level enforcement that also covers any
        future direct-ORM write. Kept only because removing a public model
        method is out of scope for this remediation; do not rely on it."""
        total = self.platform_share_percent + self.company_share_percent + self.caregiver_share_percent
        if total != 100:
            raise ValueError(f"CommissionContract shares must sum to exactly 100, got {total}.")
