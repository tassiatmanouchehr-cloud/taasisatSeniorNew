"""
CommissionRuleResolver — Financial Core PR-A.

The one canonical place that resolves "what commission split applies right
now" — Business Model Section 8's explicit requirement: "Do not scatter
percentages across settings, services, and templates. Implement one
canonical policy-resolution service." Every other service (snapshot
creation, and later PR-C's settlement allocation) must call this resolver
rather than querying PolicyService/CommissionContract directly.

Priority (Business Model Section 9), highest first:
  1. Active approved Company-Caregiver CommissionContract
  2. Platform-specific override for the applicable caregiver/company
  3. Cooperation-type default
  4. Global default

Goods shares are resolved independently, always via cooperation_type=GOODS
(Business Model Section 16: "Goods commission policy is independent") —
contracts do not cover goods; goods resolution stops at tiers 2-4.
"""

import logging
import uuid
from dataclasses import dataclass

from django.utils import timezone

from apps.commission.models.snapshot import PolicySource

from .cooperation_type import CooperationType
from .errors import SnapshotError
from .policy_service import DEFAULT_SHARES, GOODS_KEY, CommissionPolicyService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedCommissionRule:
    cooperation_type: str
    policy_source: str
    platform_rate_percent: int
    company_rate_percent: int
    caregiver_rate_percent: int
    contract_id: uuid.UUID | None = None
    policy_version_id: uuid.UUID | None = None


class CommissionRuleResolver:
    """Resolves the effective commission rule for a service line and, independently, for a goods line."""

    @classmethod
    def resolve_service_rule(
        cls,
        *,
        tenant_id: uuid.UUID,
        cooperation_type: str,
        company_party_id: uuid.UUID | None = None,
        caregiver_party_id: uuid.UUID | None = None,
        at_time=None,
    ) -> ResolvedCommissionRule:
        at_time = at_time or timezone.now()

        if cooperation_type == CooperationType.AFFILIATED and company_party_id and caregiver_party_id:
            contract_rule = cls._resolve_active_contract(
                tenant_id=tenant_id,
                company_party_id=company_party_id,
                caregiver_party_id=caregiver_party_id,
                at_time=at_time,
            )
            if contract_rule is not None:
                return contract_rule

        override = cls._resolve_platform_override(
            tenant_id=tenant_id,
            key=cooperation_type,
            company_party_id=company_party_id,
            caregiver_party_id=caregiver_party_id,
            at_time=at_time,
        )
        if override is not None:
            return override

        cooperation_default = CommissionPolicyService.get_cooperation_default(
            tenant_id=tenant_id,
            key=cooperation_type,
            at_time=at_time,
        )
        if cooperation_default is not None:
            return cls._from_version(
                cooperation_default,
                cooperation_type=cooperation_type,
                source=PolicySource.COOPERATION_DEFAULT,
            )

        return cls._resolve_global_default(tenant_id=tenant_id, key=cooperation_type, at_time=at_time)

    @classmethod
    def resolve_goods_rule(cls, *, tenant_id: uuid.UUID, at_time=None) -> ResolvedCommissionRule:
        at_time = at_time or timezone.now()

        cooperation_default = CommissionPolicyService.get_cooperation_default(
            tenant_id=tenant_id,
            key=GOODS_KEY,
            at_time=at_time,
        )
        if cooperation_default is not None:
            return cls._from_version(
                cooperation_default, cooperation_type=GOODS_KEY, source=PolicySource.COOPERATION_DEFAULT
            )

        return cls._resolve_global_default(tenant_id=tenant_id, key=GOODS_KEY, at_time=at_time)

    # --- internal helpers -------------------------------------------------

    @classmethod
    def _resolve_active_contract(cls, *, tenant_id, company_party_id, caregiver_party_id, at_time):
        from apps.commission.models.contract import CommissionContract, CommissionContractStatus

        contract = (
            CommissionContract.objects.filter(
                tenant_id=tenant_id,
                company_party_id=company_party_id,
                caregiver_party_id=caregiver_party_id,
                status=CommissionContractStatus.ACTIVE,
                effective_start__lte=at_time,
            )
            .filter(_effective_end_covers(at_time))
            .order_by("-effective_start")
            .first()
        )
        if contract is None:
            return None
        return ResolvedCommissionRule(
            cooperation_type=CooperationType.AFFILIATED,
            policy_source=PolicySource.CONTRACT,
            platform_rate_percent=contract.platform_share_percent,
            company_rate_percent=contract.company_share_percent,
            caregiver_rate_percent=contract.caregiver_share_percent,
            contract_id=contract.id,
        )

    @classmethod
    def _resolve_platform_override(cls, *, tenant_id, key, company_party_id, caregiver_party_id, at_time):
        """Remediation 8 (System Architect Review of PR #44) — documenting
        previously-undocumented behavior, not changing it: when BOTH a
        caregiver-scoped and a company-scoped platform override exist for
        the same tenant/key, the caregiver-scoped override always wins.
        This is intentional — a caregiver-specific override is the more
        specific grant (it targets exactly one individual, vs. every
        caregiver affiliated with a given company), matching the same
        "more specific wins" principle the four-tier priority chain itself
        already applies (contract > override > cooperation-type default >
        global default)."""
        if caregiver_party_id:
            version = CommissionPolicyService.get_platform_override(
                tenant_id=tenant_id,
                key=key,
                party_scope_type="caregiver",
                party_id=caregiver_party_id,
                at_time=at_time,
            )
            if version is not None:
                return cls._from_version(version, cooperation_type=key, source=PolicySource.PLATFORM_OVERRIDE)

        if company_party_id:
            version = CommissionPolicyService.get_platform_override(
                tenant_id=tenant_id,
                key=key,
                party_scope_type="company",
                party_id=company_party_id,
                at_time=at_time,
            )
            if version is not None:
                return cls._from_version(version, cooperation_type=key, source=PolicySource.PLATFORM_OVERRIDE)

        return None

    @classmethod
    def _resolve_global_default(cls, *, tenant_id, key, at_time):
        version = CommissionPolicyService.get_global_defaults(tenant_id=tenant_id, at_time=at_time)
        if version is not None:
            shares = version.rule_payload.get(key)
            if shares is None:
                raise SnapshotError(f"Active global commission policy is missing key {key!r}.")
            return ResolvedCommissionRule(
                cooperation_type=key,
                policy_source=PolicySource.GLOBAL_DEFAULT,
                platform_rate_percent=shares["platform"],
                company_rate_percent=shares["company"],
                caregiver_rate_percent=shares["caregiver"],
                policy_version_id=version.id,
            )

        # Hard fallback: no PolicyVersion exists at all for this tenant yet
        # (e.g. seed_commission_defaults has not been run). Still resolves
        # deterministically to the documented final defaults rather than
        # raising — but is NOT recorded as GLOBAL_DEFAULT-from-a-real-version
        # (policy_version_id stays None) so a snapshot reader can tell the
        # difference between "resolved from a real seeded policy" and this
        # unseeded hard fallback. Remediation 8: logged as a warning (no
        # PII) since a tenant hitting this path in real operation usually
        # means seed_commission_defaults was never run for it.
        logger.warning(
            "No seeded commission PolicyVersion found for tenant %s / key %s — falling back to hard-coded "
            "DEFAULT_SHARES; run 'manage.py seed_commission_defaults' for this tenant if this is unexpected.",
            tenant_id,
            key,
        )
        shares = DEFAULT_SHARES[key]
        return ResolvedCommissionRule(
            cooperation_type=key,
            policy_source=PolicySource.GLOBAL_DEFAULT,
            platform_rate_percent=shares["platform"],
            company_rate_percent=shares["company"],
            caregiver_rate_percent=shares["caregiver"],
            policy_version_id=None,
        )

    @staticmethod
    def _from_version(version, *, cooperation_type, source) -> ResolvedCommissionRule:
        shares = version.rule_payload
        return ResolvedCommissionRule(
            cooperation_type=cooperation_type,
            policy_source=source,
            platform_rate_percent=shares["platform"],
            company_rate_percent=shares["company"],
            caregiver_rate_percent=shares["caregiver"],
            policy_version_id=version.id,
        )


def _effective_end_covers(at_time):
    from django.db.models import Q

    return Q(effective_end__isnull=True) | Q(effective_end__gt=at_time)
