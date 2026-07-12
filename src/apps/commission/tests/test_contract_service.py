from apps.accounts.models.profiles import OrgMembershipStatus, ProfileStatus
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
        self.caregiver_supplier, self.company_supplier, self.organization, self.caregiver_user = (
            self._make_affiliated_caregiver()
        )
        self.company_party = FinancialPartyService.resolve_party_for_supplier(self.company_supplier)
        self.caregiver_party = FinancialPartyService.resolve_party_for_supplier(self.caregiver_supplier)
        self.org_admin = make_actor(self.tenant, full_name="Org Admin")
        # The real caregiver behind caregiver_party — Remediation 1 requires
        # that only THIS specific caregiver may approve/reject the contract,
        # not merely any actor holding the organization_caregiver permission.
        self.caregiver_actor = self.caregiver_user
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


class CommissionContractResourceScopedAuthorizationTest(CommissionTestCase):
    """Remediation 1 (System Architect Review of PR #44): CommissionContract
    authorization must be resource-scoped, not merely tenant-wide, and must
    enforce real organization/affiliation eligibility invariants that RBAC
    scope alone cannot express."""

    def setUp(self):
        super().setUp()
        CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.tenant.id)
        self.caregiver_supplier, self.company_supplier, self.organization, self.caregiver_user = (
            self._make_affiliated_caregiver()
        )
        self.company_party = FinancialPartyService.resolve_party_for_supplier(self.company_supplier)
        self.caregiver_party = FinancialPartyService.resolve_party_for_supplier(self.caregiver_supplier)

    def _propose(self, *, proposed_by):
        return CommissionContractService.propose(
            tenant_id=self.tenant.id,
            company_party_id=self.company_party.id,
            caregiver_party_id=self.caregiver_party.id,
            company_share_percent=20,
            caregiver_share_percent=73,
            reason="negotiated split",
            proposed_by=proposed_by,
        )

    def test_propose_denied_for_admin_scoped_to_a_different_organization(self):
        _cg2, _co2, other_org, _cg2_user = self._make_affiliated_caregiver()
        wrong_org_admin = make_actor(self.tenant, full_name="Wrong Org Admin")
        grant_permissions(
            self.tenant,
            wrong_org_admin,
            ["commission.contract.propose"],
            scope_type="organization",
            scope_id=other_org.id,
        )
        with self.assertRaises(PermissionDenied):
            self._propose(proposed_by=wrong_org_admin)

    def test_propose_allowed_for_admin_scoped_to_the_correct_organization(self):
        right_org_admin = make_actor(self.tenant, full_name="Right Org Admin")
        grant_permissions(
            self.tenant,
            right_org_admin,
            ["commission.contract.propose"],
            scope_type="organization",
            scope_id=self.organization.id,
        )
        contract = self._propose(proposed_by=right_org_admin)
        self.assertEqual(contract.status, CommissionContractStatus.PENDING_CAREGIVER_APPROVAL)

    def test_approve_denied_for_a_different_caregiver(self):
        org_admin = make_actor(self.tenant, full_name="Org Admin")
        grant_permissions(self.tenant, org_admin, ["commission.contract.propose"])
        contract = self._propose(proposed_by=org_admin)

        _cg2_supplier, _co2_supplier, _other_org, other_caregiver_user = self._make_affiliated_caregiver()
        grant_permissions(self.tenant, other_caregiver_user, ["commission.contract.approve"])

        with self.assertRaises(ContractError):
            CommissionContractService.approve(contract_id=contract.id, approved_by=other_caregiver_user)
        contract.refresh_from_db()
        self.assertEqual(contract.status, CommissionContractStatus.PENDING_CAREGIVER_APPROVAL)

    def test_reject_denied_for_a_different_caregiver(self):
        org_admin = make_actor(self.tenant, full_name="Org Admin")
        grant_permissions(self.tenant, org_admin, ["commission.contract.propose"])
        contract = self._propose(proposed_by=org_admin)

        _cg2_supplier, _co2_supplier, _other_org, other_caregiver_user = self._make_affiliated_caregiver()
        grant_permissions(self.tenant, other_caregiver_user, ["commission.contract.approve"])

        with self.assertRaises(ContractError):
            CommissionContractService.reject(contract_id=contract.id, rejected_by=other_caregiver_user)

    def test_approve_allowed_for_the_correct_caregiver(self):
        org_admin = make_actor(self.tenant, full_name="Org Admin")
        grant_permissions(self.tenant, org_admin, ["commission.contract.propose"])
        grant_permissions(self.tenant, self.caregiver_user, ["commission.contract.approve"])
        contract = self._propose(proposed_by=org_admin)

        active = CommissionContractService.approve(contract_id=contract.id, approved_by=self.caregiver_user)
        self.assertEqual(active.status, CommissionContractStatus.ACTIVE)

    def test_propose_denied_for_suspended_membership(self):
        _cg, _co, _org, _user = (self.caregiver_supplier, self.company_supplier, self.organization, self.caregiver_user)
        from apps.accounts.models.profiles import OrganizationMembership

        OrganizationMembership.objects.filter(
            organization=self.organization,
            user=self.caregiver_user,
        ).update(status=OrgMembershipStatus.SUSPENDED)

        org_admin = make_actor(self.tenant, full_name="Org Admin")
        grant_permissions(self.tenant, org_admin, ["commission.contract.propose"])
        with self.assertRaises(ContractError):
            self._propose(proposed_by=org_admin)

    def test_propose_denied_for_inactive_organization(self):
        self.organization.status = ProfileStatus.SUSPENDED
        self.organization.save(update_fields=["status"])

        org_admin = make_actor(self.tenant, full_name="Org Admin")
        grant_permissions(self.tenant, org_admin, ["commission.contract.propose"])
        with self.assertRaises(ContractError):
            self._propose(proposed_by=org_admin)

    def test_approve_denied_when_affiliation_ended_after_proposal(self):
        from apps.accounts.models.profiles import OrganizationMembership

        org_admin = make_actor(self.tenant, full_name="Org Admin")
        grant_permissions(self.tenant, org_admin, ["commission.contract.propose"])
        grant_permissions(self.tenant, self.caregiver_user, ["commission.contract.approve"])
        contract = self._propose(proposed_by=org_admin)

        OrganizationMembership.objects.filter(
            organization=self.organization,
            user=self.caregiver_user,
        ).update(status=OrgMembershipStatus.REMOVED)

        with self.assertRaises(ContractError):
            CommissionContractService.approve(contract_id=contract.id, approved_by=self.caregiver_user)
        contract.refresh_from_db()
        self.assertEqual(contract.status, CommissionContractStatus.PENDING_CAREGIVER_APPROVAL)
