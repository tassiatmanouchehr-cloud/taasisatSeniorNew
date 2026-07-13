"""
Commission contract authorization helpers — Financial Core PR-A Remediation
(System Architect Review of PR #44, Remediation 1).

CommissionContractService's four write actions previously only enforced a
tenant-wide permission_key check via PermissionService's require call (the
actor, the permission key, and tenant_id — nothing narrower) — any actor
holding the permission anywhere in the tenant could propose/approve/reject
/terminate a contract for ANY company/caregiver pair in that tenant, and a
suspended membership or an inactive organization was never checked at all.
This module adds two closes, both layered on top of (not instead of) that
existing tenant-wide permission check:

1. Resource scoping: resolve the real organization behind a
   CommissionContract's company_party and pass a
   scope_type "organization" / scope_id <org id> pair into the same
   require call — the same scope shape
   apps.accounts.services.organization_rbac already writes for
   organization-admin RoleAssignments. Falls back to unscoped (None)
   enforcement, unchanged from pre-remediation behavior, when the
   organization cannot be resolved (e.g. a bare test ServiceSupplier with no
   accounts-side profile) rather than raising.

2. Domain ownership/eligibility invariants that RBAC scope alone cannot
   express (an "organization_caregiver" RBAC grant is not, and is not
   expected to become, scoped to one specific caregiver — see
   apps.accounts.services.organization_rbac's own docstring for why only
   ADMIN memberships are RBAC-scope-synced today):
   - the organization behind company_party must be ACTIVE;
   - the caregiver behind caregiver_party must hold a currently-ACTIVE
     OrganizationMembership with that exact organization (a suspended or
     ended affiliation must not be usable to create or activate a
     contract);
   - only the specific caregiver named on the contract may approve/reject
     it, even if a different caregiver holds the same organization-wide
     "organization_caregiver" permission.

This module deliberately never imports CaregiverProfile/OrganizationProfile
directly — apps.commission is not on the documented allowlist for that
(apps.kernel.tests.test_architecture_guardrails
.ServiceSupplierProfileCouplingTest). All accounts-profile-aware logic is
delegated to apps.accounts.services.supplier_bridge, mirroring
apps.commission.services.snapshot_service's own established pattern for the
same constraint.
"""

import uuid

from apps.kernel.services.audit_service import AuditService

from .errors import ContractError

SOURCE_MODULE = "M05"


def organization_scope_for_company_party(company_party_id: uuid.UUID) -> dict | None:
    """{"scope_type": "organization", "scope_id": <uuid>} for the company
    behind this FinancialParty, or None if it cannot be resolved. None is
    passed through to PermissionService's require call exactly like today's
    unscoped calls."""
    from apps.accounts.services.supplier_bridge import organization_scope_for_supplier

    supplier = _resolve_supplier_for_party(company_party_id)
    if supplier is None:
        return None
    return organization_scope_for_supplier(supplier)


def assert_company_and_affiliation_active(*, company_party_id: uuid.UUID, caregiver_party_id: uuid.UUID) -> None:
    """Raises ContractError unless the company is a real, ACTIVE
    organization AND the caregiver holds a currently-ACTIVE
    OrganizationMembership with that exact organization. Required before a
    contract may be proposed (a fresh negotiation must start from a real,
    active affiliation) or approved (an affiliation may have been suspended
    or ended between propose() and approve())."""
    from apps.accounts.services.supplier_bridge import (
        is_caregiver_actively_affiliated_with_organization_supplier,
        is_organization_supplier_active,
    )

    company_supplier = _resolve_supplier_for_party(company_party_id)
    caregiver_supplier = _resolve_supplier_for_party(caregiver_party_id)

    if company_supplier is None or not is_organization_supplier_active(company_supplier):
        raise ContractError(
            "Commission contracts require a real, ACTIVE organization as the company party; "
            "the organization could not be resolved or is not active."
        )
    if caregiver_supplier is None or not is_caregiver_actively_affiliated_with_organization_supplier(
        caregiver_supplier=caregiver_supplier,
        organization_supplier=company_supplier,
    ):
        raise ContractError(
            "The caregiver has no ACTIVE OrganizationMembership with this organization; "
            "a commission contract cannot be proposed or approved for a suspended or ended affiliation."
        )


def assert_actor_is_contract_caregiver(actor, *, tenant_id: uuid.UUID, caregiver_party_id: uuid.UUID) -> None:
    """Only the specific caregiver named on the contract may approve/reject
    it — even a different caregiver holding the same tenant-wide (or
    organization-wide) 'organization_caregiver' RBAC permission must be
    denied. actor=None (true system context — mirrors PermissionService's
    own require call's actor=None contract) is exempt, since there is no
    human identity to compare against."""
    if actor is None:
        return

    from apps.accounts.services.supplier_bridge import caregiver_user_id_for_supplier

    caregiver_supplier = _resolve_supplier_for_party(caregiver_party_id)
    caregiver_user_id = caregiver_user_id_for_supplier(caregiver_supplier) if caregiver_supplier else None
    actor_user_id = _resolve_actor_user_id(actor)

    if caregiver_user_id is not None and actor_user_id is not None and caregiver_user_id == actor_user_id:
        return

    AuditService.log_security(
        tenant_id=tenant_id,
        action="commission.contract.approve.denied_wrong_caregiver",
        resource_type="CommissionContract",
        module_id=SOURCE_MODULE,
        actor_id=getattr(actor, "person_id", None),
        after={"caregiver_party_id": str(caregiver_party_id)},
        reason="Actor is not the caregiver named on this commission contract.",
    )
    raise ContractError("Only the caregiver named on this contract may approve or reject it.")


def assert_actor_is_order_customer(actor, order, *, error_cls) -> None:
    """Ownership-as-security-boundary for customer self-actions on an order
    (objection-period approval, dispute opening) — Financial Core PR-B.
    Shared by apps.commission.services.objection_service and
    apps.commission.services.dispute_service, both of which use no RBAC
    permission_key for these two customer actions, matching the portal's
    own documented "no RBAC permission keys for customer self-service"
    convention. Raises error_cls (the caller's own domain error type) if
    actor is None or does not resolve to the order's own customer."""
    if actor is None:
        raise error_cls("A real customer actor is required for this action.")
    if not order.customer_profile_id:
        raise error_cls("Order has no linked customer.")

    actor_user_id = _resolve_actor_user_id(actor)
    if actor_user_id is None or order.customer_profile.user_id != actor_user_id:
        raise error_cls("Only the customer who owns this order may perform this action.")


# --- internal helpers -------------------------------------------------


def _resolve_supplier_for_party(party_id: uuid.UUID):
    from apps.finance.models import FinancialParty
    from apps.kernel.models.supplier import ServiceSupplier

    party = FinancialParty.objects.filter(id=party_id).first()
    if party is None or party.linked_entity_type != "ServiceSupplier":
        return None
    return ServiceSupplier.objects.filter(id=party.linked_entity_id).first()


def _resolve_actor_user_id(actor) -> uuid.UUID | None:
    from apps.kernel.models.user import Person, UserAccount

    if isinstance(actor, UserAccount):
        return actor.id
    if isinstance(actor, Person):
        user = UserAccount.objects.filter(person_id=actor.id).first()
        return user.id if user else None
    return None
