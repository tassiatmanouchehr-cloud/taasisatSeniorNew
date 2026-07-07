"""
Tests for MatchOrchestrator.run() and MatchOrchestrator.mark_candidate_selected().

Critically verifies matching never assigns Order.assigned_supplier itself —
assignment stays exclusively owned by
apps.orders.services.status_machine.assign_supplier().
"""

from apps.kernel.models.supplier import AvailabilityStatus
from apps.matching.models import EligibilityCode, MatchCandidate, MatchCandidateStatus, MatchRound, MatchRoundStatus
from apps.matching.services.match_orchestrator import MatchOrchestrator
from apps.orders.services.status_machine import assign_supplier

from .helpers import MatchingTestCase


class MatchOrchestratorRunTest(MatchingTestCase):
    def test_run_creates_match_round(self):
        self._create_supplier()
        match_round = MatchOrchestrator.run(self.order.id)
        self.assertIsInstance(match_round, MatchRound)
        self.assertEqual(match_round.status, MatchRoundStatus.COMPLETED)
        self.assertEqual(match_round.order_id, self.order.id)
        self.assertEqual(match_round.tenant_id, self.tenant.id)
        self.assertIsNotNone(match_round.completed_at)

    def test_run_creates_eligible_ranked_candidate(self):
        supplier = self._create_supplier()
        match_round = MatchOrchestrator.run(self.order.id)
        candidates = MatchCandidate.objects.filter(match_round=match_round)
        self.assertEqual(candidates.count(), 1)

        candidate = candidates.first()
        self.assertEqual(candidate.supplier_id, supplier.id)
        self.assertEqual(candidate.tenant_id, self.tenant.id)
        self.assertTrue(candidate.eligible)
        self.assertEqual(candidate.eligibility_code, EligibilityCode.ELIGIBLE)
        self.assertEqual(candidate.status, MatchCandidateStatus.RANKED)
        self.assertIsNotNone(candidate.rank_score)
        self.assertEqual(candidate.rank_position, 1)

    def test_run_excludes_offline_supplier_entirely(self):
        self._create_supplier(availability_status=AvailabilityStatus.OFFLINE)
        match_round = MatchOrchestrator.run(self.order.id)
        self.assertEqual(MatchCandidate.objects.filter(match_round=match_round).count(), 0)

    def test_run_persists_on_leave_supplier_as_ineligible(self):
        """on_leave passes SupplierResolver's loose generation filter but fails eligibility."""
        self._create_supplier(availability_status=AvailabilityStatus.ON_LEAVE)
        match_round = MatchOrchestrator.run(self.order.id)
        candidates = MatchCandidate.objects.filter(match_round=match_round)
        self.assertEqual(candidates.count(), 1)

        candidate = candidates.first()
        self.assertFalse(candidate.eligible)
        self.assertEqual(candidate.eligibility_code, EligibilityCode.SUPPLIER_UNAVAILABLE)
        self.assertEqual(candidate.status, MatchCandidateStatus.GENERATED)
        self.assertIsNone(candidate.rank_score)
        self.assertIsNone(candidate.rank_position)

    def test_run_does_not_write_assigned_supplier(self):
        self._create_supplier()
        self.assertIsNone(self.order.assigned_supplier)
        MatchOrchestrator.run(self.order.id)
        self.order.refresh_from_db()
        self.assertIsNone(self.order.assigned_supplier)

    def test_run_does_not_change_order_status(self):
        self._create_supplier()
        original_status = self.order.status
        MatchOrchestrator.run(self.order.id)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, original_status)

    def test_config_snapshot_captured_on_round(self):
        match_round = MatchOrchestrator.run(self.order.id)
        self.assertIn("max_candidates", match_round.config_snapshot)
        self.assertIn("min_verification_level", match_round.config_snapshot)
        self.assertIn("ranking_weights", match_round.config_snapshot)

    def test_run_never_matches_cross_tenant_supplier(self):
        self._create_supplier(tenant=self.other_tenant)
        match_round = MatchOrchestrator.run(self.order.id)
        self.assertEqual(MatchCandidate.objects.filter(match_round=match_round).count(), 0)


class MarkCandidateSelectedTest(MatchingTestCase):
    def test_mark_selected_after_external_assignment(self):
        supplier = self._create_supplier()
        match_round = MatchOrchestrator.run(self.order.id)
        candidate = MatchCandidate.objects.get(match_round=match_round, supplier=supplier)

        # Assignment happens through the ONLY legitimate path.
        assign_supplier(order_id=self.order.id, supplier=supplier)

        updated = MatchOrchestrator.mark_candidate_selected(match_candidate_id=candidate.id)
        self.assertEqual(updated.status, MatchCandidateStatus.SELECTED)

        self.order.refresh_from_db()
        self.assertEqual(self.order.assigned_supplier_id, supplier.id)

    def test_mark_selected_does_not_perform_assignment(self):
        """mark_candidate_selected() must never itself write Order.assigned_supplier."""
        supplier = self._create_supplier()
        match_round = MatchOrchestrator.run(self.order.id)
        candidate = MatchCandidate.objects.get(match_round=match_round, supplier=supplier)

        MatchOrchestrator.mark_candidate_selected(match_candidate_id=candidate.id)

        self.order.refresh_from_db()
        self.assertIsNone(self.order.assigned_supplier)
