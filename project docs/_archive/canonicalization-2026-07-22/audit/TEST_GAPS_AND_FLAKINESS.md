# TEST GAPS AND FLAKINESS

---

## Flaky Tests

### seed_product_walkthrough Race Condition

**Test:** `apps.kernel.tests.test_seed_product_walkthrough.SeedProductWalkthroughReportSideEffectTest.test_reporting_does_not_change_service_supplier_count`

**Symptom:** IntegrityError on orders_order_order_number_key constraint

**Root cause:** `_generate_order_number()` uses random 4-digit suffix that can collide when multiple orders are created within the same second during concurrent test execution.

**Evidence:** Baseline verification proves pre-existing — passes 10/10 in isolation, fails in full regression.

**Impact:** Full regression always exits with code 1.

---

## Test Coverage Gaps

### Zero-Test Apps

| App | Risk Level | Reason |
|-----|-----------|--------|
| common | HIGH | Shared enums, managers, validators imported across multiple apps |
| showcase | LOW | Static UI component demos |

### Missing Integration Tests

No test exercises the complete chain:
Order → Matching → Assignment → Execution → Payment → Escrow → Settlement

### Missing End-to-End Portal Tests

Portal tests cover route/URL resolution and basic view rendering, but don't test complete user workflows through the browser.

### No Load/Performance Tests

No performance benchmarks or load tests exist.

### No Migration Tests

No tests verify that migrations apply cleanly to a fresh database.

---

## Test Quality Observations

| Observation | Evidence |
|-------------|----------|
| Low mock usage (5%) | Only 10/196 files use unittest.mock |
| Real DB operations | Tests overwhelmingly use PostgreSQL |
| Concurrency tests at critical paths | 5 files with threading.Barrier + select_for_update |
| Authorization tests broad | 53 files across 12 apps |
| Financial tests deep | 72/196 files (37%) |

---

## Recommended Test Additions (Priority Order)

1. Fix seed test race condition (BG-002)
2. Add common app tests (BG-013)
3. Add full-chain integration test (Order → Settlement)
4. Add migration tests
5. Add performance benchmarks
