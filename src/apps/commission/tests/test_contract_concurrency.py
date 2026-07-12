"""
Remediation 2 (System Architect Review of PR #44): real, database-backed
concurrency guarantees for CommissionContract — proving
uq_commcontract_open_pair / uq_commcontract_active_pair /
select_for_update() actually serialize concurrent writers, not just that
the application-layer pre-checks look correct in isolation.

Mirrors apps.booking.tests.test_concurrency (Epic 04) and
apps.payments.tests.test_settlement_orchestration.SettlementConcurrencyTest
(Epic 03 Sprint 1) exactly: TransactionTestCase is required because
Postgres row/unique-constraint locking cannot be observed across threads
inside TestCase's own wrapping transaction.
"""

import threading
import uuid

from django.apps import apps as django_apps
from django.db import connection
from django.test import TransactionTestCase

from apps.accounts.models.profiles import (
    CaregiverProfile,
    CaregiverProviderType,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from apps.accounts.services.supplier_bridge import (
    get_or_create_supplier_for_caregiver,
    get_or_create_supplier_for_organization,
)
from apps.commission.models.contract import CommissionContractStatus
from apps.commission.services.contract_service import CommissionContractService
from apps.commission.services.cooperation_type import CooperationType
from apps.commission.services.errors import ContractError
from apps.commission.services.policy_service import CommissionPolicyService
from apps.commission.services.resolver_service import CommissionRuleResolver
from apps.finance.services import FinancialPartyService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor


class _ContractConcurrencyFixtureMixin:
    available_apps = [app_config.name for app_config in django_apps.get_app_configs()]

    def _build_fixture(self):
        self.tenant = Tenant.objects.create(slug=f"comm-concur-{uuid.uuid4().hex[:8]}", name="Commission Concurrency")
        CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.tenant.id)

        org_user = self._make_user()
        self.organization = OrganizationProfile.objects.create(
            name="Org",
            code=f"org-{uuid.uuid4().hex[:8]}",
            admin_user=org_user,
            tenant=self.tenant,
        )
        self.company_supplier = get_or_create_supplier_for_organization(self.organization, tenant_id=self.tenant.id)

        cg_user = self._make_user()
        self.caregiver = CaregiverProfile.objects.create(
            user=cg_user,
            person=cg_user.person,
            phone=cg_user.phone,
            display_name="Caregiver",
            provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED,
        )
        self.caregiver_supplier = get_or_create_supplier_for_caregiver(self.caregiver, tenant_id=self.tenant.id)
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=cg_user,
            person=cg_user.person,
            role_type=OrgMembershipRole.CAREGIVER,
            status=OrgMembershipStatus.ACTIVE,
        )

        self.company_party = FinancialPartyService.resolve_party_for_supplier(self.company_supplier)
        self.caregiver_party = FinancialPartyService.resolve_party_for_supplier(self.caregiver_supplier)

        self.org_admin = make_actor(self.tenant, full_name="Org Admin")
        grant_permissions(self.tenant, self.org_admin, ["commission.contract.propose"])
        self.caregiver_actor = cg_user
        grant_permissions(self.tenant, self.caregiver_actor, ["commission.contract.approve"])

    def _make_user(self) -> UserAccount:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=self.tenant, full_name="Person")
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)

    def _propose(self, *, company_share=20, caregiver_share=73, reason="x"):
        return CommissionContractService.propose(
            tenant_id=self.tenant.id,
            company_party_id=self.company_party.id,
            caregiver_party_id=self.caregiver_party.id,
            company_share_percent=company_share,
            caregiver_share_percent=caregiver_share,
            reason=reason,
            proposed_by=self.org_admin,
        )


class ConcurrentProposeTest(_ContractConcurrencyFixtureMixin, TransactionTestCase):
    """Two concurrent propose() calls for the exact same (company, caregiver)
    pair — uq_commcontract_open_pair must allow exactly one to win."""

    def setUp(self):
        self._build_fixture()

    def test_concurrent_propose_exactly_one_succeeds(self):
        from apps.commission.models.contract import CommissionContract

        barrier = threading.Barrier(2)
        results = []

        def _attempt():
            try:
                barrier.wait(timeout=5)
                self._propose()
                results.append("ok")
            except ContractError as exc:
                results.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=_attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        successes = [r for r in results if r == "ok"]
        failures = [r for r in results if isinstance(r, ContractError)]
        self.assertEqual(len(successes), 1, f"expected exactly one winner, got results={results}")
        self.assertEqual(len(failures), 1)
        self.assertEqual(
            CommissionContract.objects.filter(
                tenant_id=self.tenant.id,
                status=CommissionContractStatus.PENDING_CAREGIVER_APPROVAL,
            ).count(),
            1,
        )

    def test_retry_after_integrity_failure_succeeds_once_pair_is_free(self):
        """Not a concurrency test — proves the failure path is recoverable,
        not a poisoned/unusable state: propose, reject, propose again."""
        first = self._propose()
        CommissionContractService.reject(contract_id=first.id, rejected_by=self.caregiver_actor, reason="no")

        second = self._propose(company_share=15, caregiver_share=78)
        self.assertEqual(second.status, CommissionContractStatus.PENDING_CAREGIVER_APPROVAL)
        self.assertNotEqual(second.id, first.id)


class ConcurrentApproveRejectTest(_ContractConcurrencyFixtureMixin, TransactionTestCase):
    """Two concurrent responses (approve vs reject) to the SAME PENDING
    contract — select_for_update() must serialize them so exactly one
    transition wins."""

    def setUp(self):
        self._build_fixture()
        self.contract = self._propose()

    def test_concurrent_approve_and_reject_exactly_one_wins(self):
        barrier = threading.Barrier(2)
        results = []

        def _approve():
            try:
                barrier.wait(timeout=5)
                CommissionContractService.approve(contract_id=self.contract.id, approved_by=self.caregiver_actor)
                results.append(("approve", "ok"))
            except ContractError as exc:
                results.append(("approve", exc))
            finally:
                connection.close()

        def _reject():
            try:
                barrier.wait(timeout=5)
                CommissionContractService.reject(
                    contract_id=self.contract.id,
                    rejected_by=self.caregiver_actor,
                    reason="changed my mind",
                )
                results.append(("reject", "ok"))
            except ContractError as exc:
                results.append(("reject", exc))
            finally:
                connection.close()

        threads = [threading.Thread(target=_approve), threading.Thread(target=_reject)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        oks = [r for r in results if r[1] == "ok"]
        self.assertEqual(len(oks), 1, f"expected exactly one transition to win, got results={results}")

        self.contract.refresh_from_db()
        self.assertIn(self.contract.status, (CommissionContractStatus.ACTIVE, CommissionContractStatus.REJECTED))


class SequentialSupersessionTest(_ContractConcurrencyFixtureMixin, TransactionTestCase):
    """Not a race — proves approve() supersedes EVERY previously-ACTIVE
    contract for the pair (not just its own recorded `supersedes`), so the
    resolver can never observe two ACTIVE rows for the same pair (the
    review's own 'does the resolver ever return ambiguous results?'
    question, closed here)."""

    def setUp(self):
        self._build_fixture()

    def test_second_activation_supersedes_first_no_ambiguity(self):
        from apps.commission.models.contract import CommissionContract

        first = self._propose(company_share=20, caregiver_share=73)
        CommissionContractService.approve(contract_id=first.id, approved_by=self.caregiver_actor)

        second = self._propose(company_share=10, caregiver_share=83)
        CommissionContractService.approve(contract_id=second.id, approved_by=self.caregiver_actor)

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.status, CommissionContractStatus.SUPERSEDED)
        self.assertEqual(second.status, CommissionContractStatus.ACTIVE)
        self.assertEqual(
            CommissionContract.objects.filter(
                tenant_id=self.tenant.id,
                company_party_id=self.company_party.id,
                caregiver_party_id=self.caregiver_party.id,
                status=CommissionContractStatus.ACTIVE,
            ).count(),
            1,
        )

        rule = CommissionRuleResolver.resolve_service_rule(
            tenant_id=self.tenant.id,
            cooperation_type=CooperationType.AFFILIATED,
            company_party_id=self.company_party.id,
            caregiver_party_id=self.caregiver_party.id,
        )
        self.assertEqual(rule.contract_id, second.id)
        self.assertEqual(rule.caregiver_rate_percent, 83)
