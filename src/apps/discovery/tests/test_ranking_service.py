"""
Tests for DiscoveryRankingService: deterministic weighted scoring, tie-
break by supplier id, explanation breakdown output, verification/
reputation/availability/capacity signal correctness.
"""

from decimal import Decimal

from apps.availability.services import CapacityService
from apps.discovery.services import DiscoveryRankingService
from apps.kernel.models.supplier import AvailabilityStatus, VerificationLevel

from .helpers import DiscoveryTestCase


class DiscoveryRankingServiceTest(DiscoveryTestCase):
    def test_higher_verification_level_scores_higher(self):
        premium = self._create_supplier(display_name="Premium", verification_level=VerificationLevel.PREMIUM)
        basic = self._create_supplier(display_name="Basic", verification_level=VerificationLevel.BASIC)

        ranked = DiscoveryRankingService.rank(tenant_id=self.tenant.id, suppliers=[basic, premium])

        self.assertEqual([item.supplier_id for item in ranked], [premium.id, basic.id])

    def test_reputation_score_contributes_to_ranking(self):
        higher = self._create_supplier(display_name="Higher rep", reputation_score=Decimal("90"))
        lower = self._create_supplier(display_name="Lower rep", reputation_score=Decimal("10"))

        ranked = DiscoveryRankingService.rank(tenant_id=self.tenant.id, suppliers=[lower, higher])
        self.assertEqual([item.supplier_id for item in ranked], [higher.id, lower.id])

    def test_null_reputation_score_treated_as_zero(self):
        supplier = self._create_supplier(reputation_score=None)
        ranked = DiscoveryRankingService.rank(tenant_id=self.tenant.id, suppliers=[supplier])
        self.assertEqual(Decimal(ranked[0].score_breakdown["reputation_component"]), Decimal("0"))

    def test_available_supplier_ranks_above_busy_supplier(self):
        available = self._create_supplier(display_name="Available", availability_status=AvailabilityStatus.AVAILABLE)
        busy = self._create_supplier(display_name="Busy", availability_status=AvailabilityStatus.BUSY)

        ranked = DiscoveryRankingService.rank(tenant_id=self.tenant.id, suppliers=[busy, available])
        self.assertEqual([item.supplier_id for item in ranked], [available.id, busy.id])

    def test_capacity_exceeded_supplier_ranks_lower(self):
        under_capacity = self._create_supplier(display_name="Under capacity")
        over_capacity = self._create_supplier(display_name="Over capacity")
        CapacityService.set_capacity_rule(supplier=over_capacity, max_concurrent_assignments=0)

        ranked = DiscoveryRankingService.rank(tenant_id=self.tenant.id, suppliers=[over_capacity, under_capacity])
        self.assertEqual([item.supplier_id for item in ranked], [under_capacity.id, over_capacity.id])

    def test_tie_break_is_deterministic_by_supplier_id(self):
        identical_a = self._create_supplier(display_name="A")
        identical_b = self._create_supplier(display_name="B")

        first_pass = DiscoveryRankingService.rank(tenant_id=self.tenant.id, suppliers=[identical_a, identical_b])
        second_pass = DiscoveryRankingService.rank(tenant_id=self.tenant.id, suppliers=[identical_b, identical_a])

        expected_order = sorted([identical_a.id, identical_b.id], key=str)
        self.assertEqual([item.supplier_id for item in first_pass], expected_order)
        self.assertEqual([item.supplier_id for item in second_pass], expected_order)

    def test_score_breakdown_includes_all_components(self):
        supplier = self._create_supplier(reputation_score=Decimal("42"))
        ranked = DiscoveryRankingService.rank(tenant_id=self.tenant.id, suppliers=[supplier])

        breakdown = ranked[0].score_breakdown
        for key in (
            "verification_component", "reputation_component",
            "availability_component", "capacity_component", "total_score",
        ):
            self.assertIn(key, breakdown)

    def test_ranking_is_deterministic_across_repeated_calls(self):
        suppliers = [self._create_supplier(display_name=f"S{i}") for i in range(5)]
        first = DiscoveryRankingService.rank(tenant_id=self.tenant.id, suppliers=suppliers)
        second = DiscoveryRankingService.rank(tenant_id=self.tenant.id, suppliers=suppliers)

        self.assertEqual(
            [(item.supplier_id, item.score) for item in first],
            [(item.supplier_id, item.score) for item in second],
        )

    def test_empty_supplier_list_returns_empty_ranking(self):
        self.assertEqual(DiscoveryRankingService.rank(tenant_id=self.tenant.id, suppliers=[]), [])
