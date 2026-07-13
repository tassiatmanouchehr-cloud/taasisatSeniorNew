from apps.commission.models.snapshot import CommissionSnapshot
from apps.commission.services.cooperation_type import CooperationType
from apps.commission.services.policy_service import CommissionPolicyService
from apps.commission.services.snapshot_service import CommissionSnapshotService
from apps.finance.models import FinancialPartyType

from .helpers import CommissionTestCase


class CommissionSnapshotServiceTest(CommissionTestCase):
    def setUp(self):
        super().setUp()
        CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.tenant.id)

    def test_independent_snapshot(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        snapshot = CommissionSnapshotService.create_snapshot_for_order(order=order, supplier=supplier)

        self.assertEqual(snapshot.cooperation_type, CooperationType.INDEPENDENT)
        self.assertEqual(snapshot.platform_rate_percent, 20)
        self.assertEqual(snapshot.caregiver_rate_percent, 80)
        self.assertIsNone(snapshot.company_party)
        self.assertIsNotNone(snapshot.caregiver_party)
        self.assertEqual(snapshot.goods_caregiver_rate_percent, 100)

    def test_company_direct_snapshot(self):
        order = self._make_order()
        supplier = self._make_company_supplier()
        snapshot = CommissionSnapshotService.create_snapshot_for_order(order=order, supplier=supplier)

        self.assertEqual(snapshot.cooperation_type, CooperationType.COMPANY_DIRECT)
        self.assertEqual(snapshot.platform_rate_percent, 7)
        self.assertEqual(snapshot.company_rate_percent, 93)
        self.assertIsNone(snapshot.caregiver_party)
        self.assertIsNotNone(snapshot.company_party)
        self.assertEqual(snapshot.company_party.party_type, FinancialPartyType.ORGANIZATION)

    def test_affiliated_snapshot_resolves_both_caregiver_and_company_party(self):
        order = self._make_order()
        caregiver_supplier, company_supplier, _org, _cg_user = self._make_affiliated_caregiver()

        snapshot = CommissionSnapshotService.create_snapshot_for_order(order=order, supplier=caregiver_supplier)

        self.assertEqual(snapshot.cooperation_type, CooperationType.AFFILIATED)
        self.assertEqual(snapshot.platform_rate_percent, 7)
        self.assertEqual(snapshot.company_rate_percent, 13)
        self.assertEqual(snapshot.caregiver_rate_percent, 80)
        self.assertIsNotNone(snapshot.caregiver_party)
        self.assertIsNotNone(snapshot.company_party)
        self.assertEqual(snapshot.caregiver_party.party_type, FinancialPartyType.SUPPLIER)
        self.assertEqual(snapshot.company_party.party_type, FinancialPartyType.ORGANIZATION)

    def test_snapshot_creation_is_idempotent_per_order(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        first = CommissionSnapshotService.create_snapshot_for_order(order=order, supplier=supplier)
        second = CommissionSnapshotService.create_snapshot_for_order(order=order, supplier=supplier)
        self.assertEqual(first.id, second.id)
        self.assertEqual(CommissionSnapshot.objects.filter(order=order).count(), 1)

    def test_snapshot_is_immutable(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        snapshot = CommissionSnapshotService.create_snapshot_for_order(order=order, supplier=supplier)

        snapshot.platform_rate_percent = 99
        with self.assertRaises(ValueError):
            snapshot.save()

    def test_snapshot_cannot_be_deleted(self):
        order = self._make_order()
        supplier = self._make_independent_supplier()
        snapshot = CommissionSnapshotService.create_snapshot_for_order(order=order, supplier=supplier)

        with self.assertRaises(ValueError):
            snapshot.delete()
