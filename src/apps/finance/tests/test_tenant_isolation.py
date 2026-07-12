"""Tests proving finance records are tenant-scoped and cross-tenant writes are rejected."""

from apps.finance.models import FinancialParty
from apps.finance.services import FinanceError, FinancialPartyService, PaymentService

from .helpers import FinanceTestCase


class FinanceTenantIsolationTest(FinanceTestCase):
    def test_for_tenant_scopes_financial_parties(self):
        # FinanceTestCase.setUp() already resolves one FinancialParty for
        # self.supplier as a side effect of AssignmentService.assign()
        # (Financial Core PR-A: CommissionSnapshotService.create_snapshot_for_order
        # resolves the assigned supplier's party to determine its commission
        # rate) — resolving the customer's own party here adds a second,
        # distinct one for the same tenant.
        FinancialPartyService.resolve_party_for_customer(self.customer_profile)

        self.assertEqual(FinancialParty.objects.for_tenant(self.tenant.id).count(), 2)
        self.assertEqual(FinancialParty.objects.for_tenant(self.other_tenant.id).count(), 0)

    def test_party_tenant_matches_source_object_tenant(self):
        party = FinancialPartyService.resolve_party_for_supplier(self.supplier)
        self.assertEqual(party.tenant_id, self.supplier.tenant_id)

    def test_record_payment_rejects_cross_tenant_parties(self):
        payer = FinancialPartyService.resolve_party_for_customer(self.customer_profile)
        other_supplier = self._create_supplier(tenant=self.other_tenant)
        receiver = FinancialPartyService.resolve_party_for_supplier(other_supplier)

        with self.assertRaises(FinanceError):
            PaymentService.record_payment(
                payer_party_id=payer.id,
                receiver_party_id=receiver.id,
                amount="1000",
                payment_method="MANUAL",
            )
