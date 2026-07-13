from django.test import SimpleTestCase

from apps.commission.services.allocation_calculator import AllocationCalculator, AllocationError

INDEPENDENT = {"platform_rate_percent": 20, "company_rate_percent": 0, "caregiver_rate_percent": 80}
AFFILIATED = {"platform_rate_percent": 7, "company_rate_percent": 13, "caregiver_rate_percent": 80}
COMPANY_DIRECT = {"platform_rate_percent": 7, "company_rate_percent": 93, "caregiver_rate_percent": 0}
GOODS = {"platform_rate_percent": 0, "company_rate_percent": 0, "caregiver_rate_percent": 100}


class AllocationCalculatorConservationTest(SimpleTestCase):
    """Business Model Section 13: sum(all allocation lines) == exact allocation base, for every amount."""

    AMOUNTS = [1, 2, 7, 13, 99, 101, 10_000_000, 10_000_001, 999_999_999_999]

    def test_conservation_holds_for_every_rate_set_and_amount(self):
        for rates in (INDEPENDENT, AFFILIATED, COMPANY_DIRECT, GOODS):
            for amount in self.AMOUNTS:
                with self.subTest(rates=rates, amount=amount):
                    result = AllocationCalculator.allocate(base_amount_irr=amount, **rates)
                    total = result.platform_amount_irr + result.company_amount_irr + result.caregiver_amount_irr
                    self.assertEqual(total, amount)

    def test_worked_example_10_000_000_affiliated(self):
        result = AllocationCalculator.allocate(base_amount_irr=10_000_000, **AFFILIATED)
        self.assertEqual(result.platform_amount_irr, 700_000)
        self.assertEqual(result.company_amount_irr, 1_300_000)
        self.assertEqual(result.caregiver_amount_irr, 8_000_000)

    def test_worked_example_10_000_000_independent(self):
        result = AllocationCalculator.allocate(base_amount_irr=10_000_000, **INDEPENDENT)
        self.assertEqual(result.platform_amount_irr, 2_000_000)
        self.assertEqual(result.caregiver_amount_irr, 8_000_000)

    def test_worked_example_10_000_000_company_direct(self):
        result = AllocationCalculator.allocate(base_amount_irr=10_000_000, **COMPANY_DIRECT)
        self.assertEqual(result.platform_amount_irr, 700_000)
        self.assertEqual(result.company_amount_irr, 9_300_000)

    def test_residual_goes_to_caregiver_not_platform_or_company(self):
        # 7 IRR at 7/13/80: platform=0 (7*7//100=0), company=0 (7*13//100=0), caregiver=7 (residual).
        result = AllocationCalculator.allocate(base_amount_irr=7, **AFFILIATED)
        self.assertEqual(result.platform_amount_irr, 0)
        self.assertEqual(result.company_amount_irr, 0)
        self.assertEqual(result.caregiver_amount_irr, 7)

    def test_rates_must_sum_to_100(self):
        with self.assertRaises(AllocationError):
            AllocationCalculator.allocate(
                base_amount_irr=1000,
                platform_rate_percent=10,
                company_rate_percent=10,
                caregiver_rate_percent=10,
            )

    def test_negative_base_amount_rejected(self):
        with self.assertRaises(AllocationError):
            AllocationCalculator.allocate(base_amount_irr=-1, **INDEPENDENT)

    def test_zero_amount_conserves(self):
        result = AllocationCalculator.allocate(base_amount_irr=0, **AFFILIATED)
        self.assertEqual(result.platform_amount_irr, 0)
        self.assertEqual(result.company_amount_irr, 0)
        self.assertEqual(result.caregiver_amount_irr, 0)

    def test_deterministic_repeat_calls_produce_identical_result(self):
        first = AllocationCalculator.allocate(base_amount_irr=10_000_001, **AFFILIATED)
        second = AllocationCalculator.allocate(base_amount_irr=10_000_001, **AFFILIATED)
        self.assertEqual(first, second)
