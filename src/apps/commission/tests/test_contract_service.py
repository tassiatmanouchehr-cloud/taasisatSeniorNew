from apps.commission.models.contract import CommissionContractStatus
from apps.commission.services.contract_service import CommissionContractService
from apps.commission.services.errors import ContractError
from apps.commission.services.policy_service import CommissionPolicyService
from apps.finance.services import FinancialPartyService
from apps.kernel.services.errors import PermissionDenied
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor

from .helpers import CommissionTestCase


class CommissionContractServiceTest(CommissionTestCase):
    def setUp(self):
        super().setUp()
        CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.tenant.id)
        self.caregiver_supplier, self.company_supplier, self.organization = self._make_affiliated_caregiver()
        self.company_party = FinancialPartyService.resolve_party_for_supplier(self.company_supplier)
        self.caregiver_party = FinancialPartyService.resolve_party_for_supplier(self.caregiver_supplier)
        self.org_admin = make_actor(self.tenant, full_name="Org Admin")
        self.caregiver_actor = make_actor(self.tenant, full_name="Caregiver Actor")
        grant_permissions(self.tenant, self.org_admin, ["commission.contract.propose"])
        grant_permissions(self.tenant, self.caregiver_actor, ["commission.contract.approve"])

    def test_propose_freezes_platform_share_from_current_affiliated_default(self):
        contract = CommissionContractService.propose(
            tenant_id=self.tenant.id,
            company_party_id=self.company_party.id,
            caregiver_party_id=self.caregiver_party.id,
            company_share_percent=20,
            caregiver_share_percent=73,
            reason="negotiated split",
            proposed_by=self.org_admin,
        )
        self.assertEqual(contract.platform_share_percent, 7)
        self.assertEqual(contract.status, CommissionContractStatus.PENDING_CAREGIVER_APPROVAL)

    def test_propose_rejects_split_that_does_not_leave_platform_share_intact(self):
        # platform=7, so company+caregiver must equal 93 — this proposes 100.
        with self.assertRaises(ContractError):
            CommissionContractService.propose(
                tenant_id=self.tenant.id,
                company_party_id=self.company_party.id,
                caregiver_party_id=self.caregiver_party.id,
                company_share_percent=50,
                caregiver_share_percent=50,
                reason="invalid",
                proposed_by=self.org_admin,
            )

    def test_propose_denied_without_permission(self):
        unauthorized = make_actor(self.tenant, full_name="No Permission")
        with self.assertRaises(PermissionDenied):
            CommissionContractService.propose(
                tenant_id=self.tenant.id,
                company_party_id=self.company_party.id,
                caregiver_party_id=self.caregiver_party.id,
                company_share_percent=20,
                caregiver_share_percent=73,
                reason="x",
                proposed_by=unauthorized,
            )

    def test_approve_activates_contract(self):
        contract = CommissionContractService.propose(
            tenant_id=self.tenant.id,
            company_party_id=self.company_party.id,
            caregiver_party_id=self.caregiver_party.id,
            company_share_percent=20,
            caregiver_share_percent=73,
            reason="negotiated split",
            proposed_by=self.org_admin,
        )
        active = CommissionContractService.approve(contract_id=contract.id, approved_by=self.caregiver_actor)
        self.assertEqual(active.status, CommissionContractStatus.ACTIVE)
        self.assertIsNotNone(active.approved_at)

    def test_approve_denied_without_permission(self):
        contract = CommissionContractService.propose(
            tenant_id=self.tenant.id,
            company_party_id=self.company_party.id,
            caregiver_party_id=self.caregiver_party.id,
            company_share_percent=20,
            caregiver_share_percent=73,
            reason="x",
            proposed_by=self.org_admin,
        )
        unauthorized = make_actor(self.tenant, full_name="No Permission")
        with self.assertRaises(PermissionDenied):
            CommissionContractService.approve(contract_id=contract.id, approved_by=unauthorized)

    def test_reject_leaves_contract_rejected(self):
        contract = CommissionContractService.propose(
            tenant_id=self.tenant.id,
            company_party_id=self.company_party.id,
            caregiver_party_id=self.caregiver_party.id,
            company_share_percent=20,
            caregiver_share_percent=73,
            reason="x",
            proposed_by=self.org_admin,
        )
        rejected = CommissionContractService.reject(
            contract_id=contract.id,
            rejected_by=self.caregiver_actor,
            reason="not acceptable",
        )
        self.assertEqual(rejected.status, CommissionContractStatus.REJECTED)

    def test_cannot_propose_second_open_contract_for_same_pair(self):
        CommissionContractService.propose(
            tenant_id=self.tenant.id,
            company_party_id=self.company_party.id,
            caregiver_party_id=self.caregiver_party.id,
            company_share_percent=20,
            caregiver_share_percent=73,
            reason="first",
            proposed_by=self.org_admin,
        )
        with self.assertRaises(ContractError):
            CommissionContractService.propose(
                tenant_id=self.tenant.id,
                company_party_id=self.company_party.id,
                caregiver_party_id=self.caregiver_party.id,
                company_share_percent=25,
                caregiver_share_percent=68,
                reason="second",
                proposed_by=self.org_admin,
            )

    def test_terminate_requires_platform_permission_not_org_admin(self):
        contract = CommissionContractService.propose(
            tenant_id=self.tenant.id,
            company_party_id=self.company_party.id,
            caregiver_party_id=self.caregiver_party.id,
            company_share_percent=20,
            caregiver_share_percent=73,
            reason="x",
            proposed_by=self.org_admin,
        )
        CommissionContractService.approve(contract_id=contract.id, approved_by=self.caregiver_actor)

        with self.assertRaises(PermissionDenied):
            CommissionContractService.terminate(contract_id=contract.id, terminated_by=self.org_admin)

        platform_actor = make_actor(self.tenant, full_name="Platform Accounting")
        grant_permissions(self.tenant, platform_actor, ["commission.contract.terminate"])
        terminated = CommissionContractService.terminate(
            contract_id=contract.id,
            terminated_by=platform_actor,
            reason="cooperation ended",
        )
        self.assertEqual(terminated.status, CommissionContractStatus.TERMINATED)

    def test_active_contract_takes_priority_over_platform_override_and_defaults(self):
        from apps.commission.models.snapshot import PolicySource
        from apps.commission.services.cooperation_type import CooperationType
        from apps.commission.services.resolver_service import CommissionRuleResolver

        contract = CommissionContractService.propose(
            tenant_id=self.tenant.id,
            company_party_id=self.company_party.id,
            caregiver_party_id=self.caregiver_party.id,
            company_share_percent=10,
            caregiver_share_percent=83,
            reason="negotiated",
            proposed_by=self.org_admin,
        )
        CommissionContractService.approve(contract_id=contract.id, approved_by=self.caregiver_actor)

        rule = CommissionRuleResolver.resolve_service_rule(
            tenant_id=self.tenant.id,
            cooperation_type=CooperationType.AFFILIATED,
            company_party_id=self.company_party.id,
            caregiver_party_id=self.caregiver_party.id,
        )
        self.assertEqual(rule.policy_source, PolicySource.CONTRACT)
        self.assertEqual(rule.company_rate_percent, 10)
        self.assertEqual(rule.caregiver_rate_percent, 83)
        self.assertEqual(rule.contract_id, contract.id)
