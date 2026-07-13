"""
CommissionSnapshotService — Financial Core PR-A.

Creates the immutable CommissionSnapshot at proposal/offer acceptance (see
apps.commission.models.snapshot.CommissionSnapshot's own docstring for why
this is the correct freeze point and why accepted_gross_amount is nullable
in PR-A).

company_party resolution for AFFILIATED orders is best-effort: it walks
CaregiverProfile -> its active OrganizationMembership -> OrganizationProfile
-> that organization's own ServiceSupplier -> that ServiceSupplier's
FinancialParty, using only existing, unmodified bridges
(apps.accounts.services.supplier_bridge,
apps.finance.services.party_service.FinancialPartyService). If any step is
unresolvable (e.g. a caregiver whose ServiceSupplier is ORGANIZATION_PROVIDER
but who has no APPROVED OrganizationMembership row yet — a data-consistency
edge case, not expected in normal operation), company_party is left None
and the snapshot still records the correct company_rate_percent from the
resolver; only the party *identity* linkage is deferred. Full multi-party
wallet/ledger wiring is explicitly PR-C's scope, not PR-A's — see the PR-A
final report's "known limitations" section.
"""

from django.db import transaction
from django.utils import timezone

from apps.finance.services import FinancialPartyService
from apps.kernel.models.audit import AuditClassification
from apps.kernel.services.audit_service import AuditService

from ..models.snapshot import CommissionSnapshot
from .cooperation_type import CooperationType, resolve_cooperation_type
from .resolver_service import CommissionRuleResolver

SOURCE_MODULE = "M05"


class CommissionSnapshotService:
    @classmethod
    @transaction.atomic
    def create_snapshot_for_order(cls, *, order, supplier, actor=None) -> CommissionSnapshot:
        existing = CommissionSnapshot.objects.filter(order=order, supplier=supplier).order_by("-created_at").first()
        if existing is not None:
            # Idempotent for a repeated call against the SAME (order,
            # supplier) pair — e.g. a retried assign() in the same
            # acceptance cycle. A reassignment to a DIFFERENT supplier
            # (after a payment-deadline expiry reopens the order) is not
            # matched here and correctly falls through to a fresh
            # resolution below, per this model's own docstring.
            return existing

        cooperation_type = resolve_cooperation_type(supplier=supplier)

        caregiver_party = None
        company_party = None

        if cooperation_type == CooperationType.COMPANY_DIRECT:
            company_party = FinancialPartyService.resolve_party_for_supplier(supplier)
        else:
            caregiver_party = FinancialPartyService.resolve_party_for_supplier(supplier)
            if cooperation_type == CooperationType.AFFILIATED:
                company_party = cls._resolve_company_party_for_caregiver(supplier=supplier)

        service_rule = CommissionRuleResolver.resolve_service_rule(
            tenant_id=order.tenant_id,
            cooperation_type=cooperation_type,
            company_party_id=company_party.id if company_party else None,
            caregiver_party_id=caregiver_party.id if caregiver_party else None,
        )
        goods_rule = CommissionRuleResolver.resolve_goods_rule(tenant_id=order.tenant_id)

        snapshot = CommissionSnapshot.objects.create(
            tenant_id=order.tenant_id,
            order=order,
            supplier=supplier,
            cooperation_type=cooperation_type,
            policy_source=service_rule.policy_source,
            contract_id=service_rule.contract_id,
            policy_version_id=service_rule.policy_version_id,
            platform_rate_percent=service_rule.platform_rate_percent,
            company_rate_percent=service_rule.company_rate_percent,
            caregiver_rate_percent=service_rule.caregiver_rate_percent,
            goods_platform_rate_percent=goods_rule.platform_rate_percent,
            goods_company_rate_percent=goods_rule.company_rate_percent,
            goods_caregiver_rate_percent=goods_rule.caregiver_rate_percent,
            company_party=company_party,
            caregiver_party=caregiver_party,
            effective_timestamp=timezone.now(),
        )

        AuditService.log(
            tenant_id=order.tenant_id,
            action="commission.snapshot.create",
            resource_type="CommissionSnapshot",
            module_id=SOURCE_MODULE,
            actor_id=getattr(actor, "person_id", None),
            resource_id=snapshot.id,
            audit_class=AuditClassification.FINANCIAL,
            after={
                "order_id": str(order.id),
                "cooperation_type": cooperation_type,
                "policy_source": service_rule.policy_source,
                "platform_rate_percent": service_rule.platform_rate_percent,
                "company_rate_percent": service_rule.company_rate_percent,
                "caregiver_rate_percent": service_rule.caregiver_rate_percent,
            },
        )

        return snapshot

    @classmethod
    def _resolve_company_party_for_caregiver(cls, *, supplier):
        from apps.accounts.services.supplier_bridge import resolve_organization_supplier_for_caregiver

        organization_supplier = resolve_organization_supplier_for_caregiver(supplier, tenant_id=supplier.tenant_id)
        if organization_supplier is None:
            return None
        return FinancialPartyService.resolve_party_for_supplier(organization_supplier)
