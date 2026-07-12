import uuid

from apps.commission.services.contract_service import CommissionContractService
from apps.commission.services.cooperation_type import CooperationType
from apps.commission.services.deadline_service import PaymentDeadlineService
from apps.commission.services.policy_service import CommissionPolicyService
from apps.commission.services.resolver_service import CommissionRuleResolver
from apps.commission.services.snapshot_service import CommissionSnapshotService
from apps.finance.services import FinancialPartyService
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor

from .helpers import CommissionTestCase


class CommissionTenantIsolationTest(CommissionTestCase):
    """Adversarial: an object ID that genuinely exists (in another tenant)
    must never be reachable from a different tenant's context."""

    def setUp(self):
        super().setUp()
        CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.tenant.id)
        CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.other_tenant.id)

    def test_platform_override_scoped_to_its_own_tenant_only(self):
        caregiver_party_id = uuid.uuid4()
        CommissionPolicyService.set_platform_override(
            tenant_id=self.tenant.id,
            key=CooperationType.INDEPENDENT,
            party_scope_type="caregiver",
            party_id=caregiver_party_id,
            shares={"platform": 5, "company": 0, "caregiver": 95},
            change_reason="test",
            auto_activate=True,
        )

        other_tenant_rule = CommissionRuleResolver.resolve_service_rule(
            tenant_id=self.other_tenant.id,
            cooperation_type=CooperationType.INDEPENDENT,
            caregiver_party_id=caregiver_party_id,
        )
        # The same caregiver_party_id under a DIFFERENT tenant must never
        # see the other tenant's override — falls through to that tenant's
        # own global default (20/80) instead.
        self.assertEqual(other_tenant_rule.platform_rate_percent, 20)

    def test_contract_from_other_tenant_cannot_be_approved_via_this_tenants_permission(self):
        caregiver_supplier, company_supplier, _org, cg_user = self._make_affiliated_caregiver(tenant=self.other_tenant)
        company_party = FinancialPartyService.resolve_party_for_supplier(company_supplier)
        caregiver_party = FinancialPartyService.resolve_party_for_supplier(caregiver_supplier)

        proposer = make_actor(self.other_tenant, full_name="Other Tenant Org Admin")
        grant_permissions(self.other_tenant, proposer, ["commission.contract.propose"])
        contract = CommissionContractService.propose(
            tenant_id=self.other_tenant.id,
            company_party_id=company_party.id,
            caregiver_party_id=caregiver_party.id,
            company_share_percent=20,
            caregiver_share_percent=73,
            reason="x",
            proposed_by=proposer,
        )

        # An actor who only has approve-permission granted in the FIRST
        # tenant must still be denied on a contract that belongs to the
        # OTHER tenant — PermissionService itself is tenant-scoped, and
        # approve() passes contract.tenant_id (the object's real tenant),
        # never the caller's assumed tenant.
        wrong_tenant_actor = make_actor(self.tenant, full_name="Wrong Tenant Caregiver")
        grant_permissions(self.tenant, wrong_tenant_actor, ["commission.contract.approve"])

        from apps.kernel.services.errors import PermissionDenied

        with self.assertRaises(PermissionDenied):
            CommissionContractService.approve(contract_id=contract.id, approved_by=wrong_tenant_actor)

    def test_snapshot_and_deadline_are_tenant_scoped_via_tenant_scoped_manager(self):
        order = self._make_order(tenant=self.tenant)
        supplier = self._make_independent_supplier(tenant=self.tenant)
        snapshot = CommissionSnapshotService.create_snapshot_for_order(order=order, supplier=supplier)
        deadline = PaymentDeadlineService.create_for_order(order=order)

        from apps.commission.models.deadline import PaymentDeadline
        from apps.commission.models.snapshot import CommissionSnapshot

        self.assertFalse(CommissionSnapshot.objects.filter(tenant_id=self.other_tenant.id, id=snapshot.id).exists())
        self.assertFalse(PaymentDeadline.objects.filter(tenant_id=self.other_tenant.id, id=deadline.id).exists())
        self.assertTrue(CommissionSnapshot.objects.filter(tenant_id=self.tenant.id, id=snapshot.id).exists())
