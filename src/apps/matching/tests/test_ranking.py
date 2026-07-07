"""Tests for RankingService: determinism and score_breakdown."""

from apps.kernel.models.supplier import VerificationLevel
from apps.matching.services.ranking import RankingService

from .helpers import MatchingTestCase


class RankingServiceTest(MatchingTestCase):
    def test_higher_verification_ranks_first(self):
        low = self._create_supplier(verification_level=VerificationLevel.BASIC)
        high = self._create_supplier(verification_level=VerificationLevel.PREMIUM)
        ranked = RankingService.rank(order=self.order, candidates=[low, high])
        suppliers_in_order = [supplier for supplier, _score, _breakdown in ranked]
        self.assertEqual(suppliers_in_order, [high, low])

    def test_score_breakdown_present(self):
        supplier = self._create_supplier()
        ranked = RankingService.rank(order=self.order, candidates=[supplier])
        _, score, breakdown = ranked[0]
        self.assertIsNotNone(score)
        self.assertIn("verification_component", breakdown)
        self.assertIn("reputation_component", breakdown)
        self.assertIn("availability_component", breakdown)

    def test_ranking_is_deterministic_regardless_of_input_order(self):
        a = self._create_supplier(verification_level=VerificationLevel.BASIC)
        b = self._create_supplier(verification_level=VerificationLevel.BASIC)
        first_run = [supplier.id for supplier, _s, _b in RankingService.rank(order=self.order, candidates=[a, b])]
        second_run = [supplier.id for supplier, _s, _b in RankingService.rank(order=self.order, candidates=[b, a])]
        self.assertEqual(first_run, second_run)

    def test_empty_candidates_returns_empty(self):
        self.assertEqual(RankingService.rank(order=self.order, candidates=[]), [])

    def test_null_reputation_treated_as_zero_not_error(self):
        supplier = self._create_supplier(reputation_score=None)
        ranked = RankingService.rank(order=self.order, candidates=[supplier])
        self.assertEqual(len(ranked), 1)
