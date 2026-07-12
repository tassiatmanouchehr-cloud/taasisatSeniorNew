"""
CommissionPolicyService — Financial Core PR-A.

Thin, commission-specific wrapper around the existing, generic
apps.kernel.services.policy_service.PolicyService (PolicyDefinition +
PolicyVersion — "Major business rules... are implemented as versioned
policies... immutable version snapshots... only one version active at a
time per policy", per that module's own docstring). Reused rather than
duplicated, per the explicit instruction to reuse approved existing
services where they are correct.

Encodes exactly two scope tiers on top of the generic policy engine (tier 1,
the Company-Caregiver Contract, is a dedicated model — see
contract_service.py — because its negotiation/approval shape does not fit
PolicyVersion's simpler lifecycle):

  Tier 4 — GLOBAL_DEFAULT:   policy_type="commission", scope_type="tenant",
                              name=GLOBAL_POLICY_NAME. One PolicyVersion's
                              rule_payload bulk-holds all four splits
                              (INDEPENDENT/AFFILIATED/COMPANY_DIRECT/GOODS)
                              at once, so "change all global defaults
                              together" (Business Model Section 8) is one
                              atomic version activation.
  Tier 3 — COOPERATION_DEFAULT: policy_type="commission",
                              scope_type="cooperation_type",
                              name=cooperation_policy_name(key). A more
                              specific override of exactly one of the four
                              splits, without touching the global bucket.
  Tier 2 — PLATFORM_OVERRIDE: policy_type="commission",
                              scope_type="caregiver"|"company",
                              scope_id=<FinancialParty.id>,
                              name=cooperation_policy_name(key). A
                              per-entity override, still platform-controlled
                              (an organization admin never reaches this
                              service — see contract_service.py for the
                              org-admin-facing surface, which can only ever
                              touch a CommissionContract).

Every rule_payload here is the single shape {"platform": int, "company":
int, "caregiver": int} (company omitted/0 for INDEPENDENT; caregiver
omitted/0 for COMPANY_DIRECT) — shares in whole percent, validated to sum
to exactly 100 before any version may be created.
"""

import uuid
from typing import Any

from django.utils import timezone

from apps.kernel.models.policy import PolicyVersion
from apps.kernel.services.permission_service import PermissionService
from apps.kernel.services.policy_service import PolicyService

from ..permission_keys import COMMISSION_POLICY_MANAGE
from .cooperation_type import CooperationType
from .errors import InvalidPolicyError

POLICY_TYPE = "commission"
GLOBAL_POLICY_NAME = "commission_global_defaults"

GOODS_KEY = "GOODS"
ALL_KEYS = (CooperationType.INDEPENDENT, CooperationType.AFFILIATED, CooperationType.COMPANY_DIRECT, GOODS_KEY)

# Final owner-decided defaults (Business Model Section 7 / Section 16).
# These are seed defaults, not permanent constants — every one is
# reconfigurable via CommissionPolicyService.set_global_defaults()/
# set_cooperation_default()/set_platform_override().
DEFAULT_SHARES: dict[str, dict[str, int]] = {
    CooperationType.INDEPENDENT: {"platform": 20, "company": 0, "caregiver": 80},
    CooperationType.AFFILIATED: {"platform": 7, "company": 13, "caregiver": 80},
    CooperationType.COMPANY_DIRECT: {"platform": 7, "company": 93, "caregiver": 0},
    GOODS_KEY: {"platform": 0, "company": 0, "caregiver": 100},
}


def cooperation_policy_name(key: str) -> str:
    return f"commission_{key.lower()}"


def override_policy_name(*, key: str, party_scope_type: str, party_id: uuid.UUID) -> str:
    """Distinct from cooperation_policy_name(key): PolicyDefinition's own
    uniqueness is scoped to (tenant_id, policy_type, name) only — NOT
    scope_type/scope_id — so a tier-2 (per-party) override must never reuse
    the same name as its tier-3 (cooperation-type) sibling, or
    PolicyService.create_policy's get_or_create would silently collapse
    them into the same PolicyDefinition row instead of two independent
    ones."""
    return f"commission_override_{party_scope_type}_{party_id}_{key.lower()}"


def validate_shares(shares: dict[str, Any], *, key: str) -> None:
    required = {"platform", "company", "caregiver"}
    missing = required - set(shares)
    if missing:
        raise InvalidPolicyError(f"Commission shares for {key} missing field(s): {sorted(missing)}.")

    for field in required:
        value = shares[field]
        if not isinstance(value, int) or isinstance(value, bool):
            raise InvalidPolicyError(f"Commission share {key}.{field} must be an int, got {type(value).__name__}.")
        if value < 0 or value > 100:
            raise InvalidPolicyError(f"Commission share {key}.{field}={value} must be between 0 and 100.")

    total = shares["platform"] + shares["company"] + shares["caregiver"]
    if total != 100:
        raise InvalidPolicyError(f"Commission shares for {key} must sum to exactly 100, got {total}.")


def validate_global_payload(payload: dict[str, Any]) -> None:
    missing = set(ALL_KEYS) - set(payload)
    if missing:
        raise InvalidPolicyError(f"Global commission policy payload missing key(s): {sorted(missing)}.")
    for key in ALL_KEYS:
        validate_shares(payload[key], key=key)


class CommissionPolicyService:
    """Creates/activates/resolves commission PolicyVersions via the canonical kernel PolicyService."""

    @classmethod
    def set_global_defaults(
        cls,
        *,
        tenant_id: uuid.UUID,
        payload: dict[str, dict[str, int]],
        change_reason: str,
        actor=None,
        auto_activate: bool = True,
    ) -> PolicyVersion:
        PermissionService.require(actor, COMMISSION_POLICY_MANAGE, tenant_id=tenant_id)
        validate_global_payload(payload)
        return PolicyService.create_policy(
            tenant_id=tenant_id,
            policy_type=POLICY_TYPE,
            name=GLOBAL_POLICY_NAME,
            owner_module="M05",
            rule_payload=payload,
            scope_type="tenant",
            scope_id=None,
            change_reason=change_reason,
            created_by=getattr(actor, "person_id", None),
            auto_activate=auto_activate,
            description="Bulk global default commission shares for all cooperation types + goods.",
        )

    @classmethod
    def set_cooperation_default(
        cls,
        *,
        tenant_id: uuid.UUID,
        key: str,
        shares: dict[str, int],
        change_reason: str,
        actor=None,
        auto_activate: bool = True,
    ) -> PolicyVersion:
        PermissionService.require(actor, COMMISSION_POLICY_MANAGE, tenant_id=tenant_id)
        validate_shares(shares, key=key)
        return PolicyService.create_policy(
            tenant_id=tenant_id,
            policy_type=POLICY_TYPE,
            name=cooperation_policy_name(key),
            owner_module="M05",
            rule_payload=shares,
            scope_type="cooperation_type",
            scope_id=None,
            change_reason=change_reason,
            created_by=getattr(actor, "person_id", None),
            auto_activate=auto_activate,
            description=f"Cooperation-type default commission shares for {key}.",
        )

    @classmethod
    def set_platform_override(
        cls,
        *,
        tenant_id: uuid.UUID,
        key: str,
        party_scope_type: str,
        party_id: uuid.UUID,
        shares: dict[str, int],
        change_reason: str,
        actor=None,
        auto_activate: bool = True,
    ) -> PolicyVersion:
        PermissionService.require(actor, COMMISSION_POLICY_MANAGE, tenant_id=tenant_id)
        if party_scope_type not in ("company", "caregiver"):
            raise InvalidPolicyError(f"party_scope_type must be 'company' or 'caregiver', got {party_scope_type!r}.")
        validate_shares(shares, key=key)
        return PolicyService.create_policy(
            tenant_id=tenant_id,
            policy_type=POLICY_TYPE,
            name=override_policy_name(key=key, party_scope_type=party_scope_type, party_id=party_id),
            owner_module="M05",
            rule_payload=shares,
            scope_type=party_scope_type,
            scope_id=party_id,
            change_reason=change_reason,
            created_by=getattr(actor, "person_id", None),
            auto_activate=auto_activate,
            description=f"Platform-specific commission override for {party_scope_type} {party_id} ({key}).",
        )

    @classmethod
    def get_cooperation_default(cls, *, tenant_id: uuid.UUID, key: str, at_time=None) -> PolicyVersion | None:
        return PolicyService.get_active_version(
            tenant_id=tenant_id,
            policy_type=POLICY_TYPE,
            policy_name=cooperation_policy_name(key),
            scope_type="cooperation_type",
            at_time=at_time,
        )

    @classmethod
    def get_platform_override(
        cls,
        *,
        tenant_id: uuid.UUID,
        key: str,
        party_scope_type: str,
        party_id: uuid.UUID,
        at_time=None,
    ) -> PolicyVersion | None:
        return PolicyService.get_active_version(
            tenant_id=tenant_id,
            policy_type=POLICY_TYPE,
            policy_name=override_policy_name(key=key, party_scope_type=party_scope_type, party_id=party_id),
            scope_type=party_scope_type,
            scope_id=party_id,
            at_time=at_time,
        )

    @classmethod
    def get_global_defaults(cls, *, tenant_id: uuid.UUID, at_time=None) -> PolicyVersion | None:
        return PolicyService.get_active_version(
            tenant_id=tenant_id,
            policy_type=POLICY_TYPE,
            policy_name=GLOBAL_POLICY_NAME,
            scope_type="tenant",
            at_time=at_time,
        )

    @classmethod
    def seed_defaults_if_missing(cls, *, tenant_id: uuid.UUID, actor=None) -> PolicyVersion | None:
        """Idempotent: only seeds the global-default bucket if none is active yet.
        Never overwrites an existing configuration — safe to call from a
        management command or app-ready hook without clobbering a platform
        owner's prior changes. actor=None (the default) is the documented
        system-context bypass (apps.kernel.services.permission_service
        .PermissionService's own docstring) — the intended caller is a
        one-time bootstrap management command, not a human request."""
        existing = cls.get_global_defaults(tenant_id=tenant_id)
        if existing is not None:
            return None
        return cls.set_global_defaults(
            tenant_id=tenant_id,
            payload=DEFAULT_SHARES,
            change_reason="Initial seed of Financial Core default commission policies (PR-A).",
            actor=actor,
            auto_activate=True,
        )


def now():
    return timezone.now()
