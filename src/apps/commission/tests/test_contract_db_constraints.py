"""Remediation 3 (System Architect Review of PR #44): DB-level enforcement
of CommissionContract's share invariants — proving a direct-ORM write (not
just CommissionContractService.propose()) is rejected by the database
itself, not merely by application-layer validation."""

from django.db import IntegrityError, transaction

from apps.commission.models.contract import CommissionContract, CommissionContractStatus
from apps.finance.services import FinancialPartyService

from .helpers import CommissionTestCase


class CommissionContractDbConstraintTest(CommissionTestCase):
    def setUp(self):
        super().setUp()
        company_supplier = self._make_company_supplier()
        caregiver_supplier = self._make_independent_supplier()
        self.company_party = FinancialPartyService.resolve_party_for_supplier(company_supplier)
        self.caregiver_party = FinancialPartyService.resolve_party_for_supplier(caregiver_supplier)

    def _create(self, *, platform, company, caregiver, status=CommissionContractStatus.DRAFT):
        return CommissionContract.objects.create(
            tenant_id=self.tenant.id,
            company_party=self.company_party,
            caregiver_party=self.caregiver_party,
            status=status,
            platform_share_percent=platform,
            company_share_percent=company,
            caregiver_share_percent=caregiver,
        )

    def test_valid_splits_accepted_directly_via_orm(self):
        for platform, company, caregiver in [(20, 0, 80), (7, 13, 80), (7, 93, 0), (0, 0, 100)]:
            # A fresh pair per iteration — uq_commcontract_open_pair allows
            # only one DRAFT/PENDING row per (tenant, company, caregiver);
            # this loop is testing the share-range/sum constraints, not
            # pair uniqueness (covered separately below).
            company_supplier = self._make_company_supplier()
            caregiver_supplier = self._make_independent_supplier()
            company_party = FinancialPartyService.resolve_party_for_supplier(company_supplier)
            caregiver_party = FinancialPartyService.resolve_party_for_supplier(caregiver_supplier)
            with transaction.atomic():
                contract = CommissionContract.objects.create(
                    tenant_id=self.tenant.id,
                    company_party=company_party,
                    caregiver_party=caregiver_party,
                    status=CommissionContractStatus.DRAFT,
                    platform_share_percent=platform,
                    company_share_percent=company,
                    caregiver_share_percent=caregiver,
                )
            self.assertEqual(contract.platform_share_percent, platform)

    def test_sum_below_100_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._create(platform=20, company=0, caregiver=70)

    def test_sum_above_100_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._create(platform=20, company=0, caregiver=90)

    def test_negative_share_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            CommissionContract.objects.create(
                tenant_id=self.tenant.id,
                company_party=self.company_party,
                caregiver_party=self.caregiver_party,
                status=CommissionContractStatus.DRAFT,
                platform_share_percent=120,
                company_share_percent=-20,
                caregiver_share_percent=0,
            )

    def test_share_above_100_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._create(platform=0, company=150, caregiver=-50)

    def test_only_one_open_proposal_per_pair_at_db_level(self):
        self._create(platform=20, company=0, caregiver=80, status=CommissionContractStatus.PENDING_CAREGIVER_APPROVAL)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._create(
                platform=7,
                company=13,
                caregiver=80,
                status=CommissionContractStatus.PENDING_CAREGIVER_APPROVAL,
            )

    def test_only_one_active_contract_per_pair_at_db_level(self):
        self._create(platform=20, company=0, caregiver=80, status=CommissionContractStatus.ACTIVE)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._create(platform=7, company=13, caregiver=80, status=CommissionContractStatus.ACTIVE)

    def test_rejected_and_terminated_contracts_do_not_collide(self):
        # REJECTED/TERMINATED/SUPERSEDED are not in either unique
        # constraint's condition — many terminal-status rows for the same
        # pair must coexist (contract history).
        self._create(platform=20, company=0, caregiver=80, status=CommissionContractStatus.REJECTED)
        self._create(platform=7, company=13, caregiver=80, status=CommissionContractStatus.REJECTED)
        self._create(platform=7, company=13, caregiver=80, status=CommissionContractStatus.TERMINATED)
        self.assertEqual(CommissionContract.objects.filter(tenant_id=self.tenant.id).count(), 3)
