# FINAL CONTRACT REMEDIATION REPORT

**Repository:** taasisatSenior
**Contract:** OFFER_MARKETPLACE_IMPLEMENTATION_CONTRACT.md
**Date:** July 13, 2026

---

## 1. Previous Issue — Marketplace Visibility During Active Hold

**Issue:** The contract stated "Other caregivers can still see the order (it's still available)" during an active hold. This contradicted the requirement that the order should be hidden from the marketplace while reserved.

**Evidence:** Section 1.5 of the contract explicitly said the order remains visible. No discovery query guard was specified.

**Decision:** Add a `NOT EXISTS` subquery guard to the discovery service: orders with a SELECTED offer are hidden from the caregiver marketplace list.

**Contract sections changed:** Section 1.5 (rewritten), Section 12 (discovery service query specification added)

**Before behavior:** Order visible to all caregivers during hold. New offers could be submitted on a held order.

**After behavior:** Order hidden from marketplace during hold. No new offers can be submitted. Existing stored offers remain unchanged.

---

## 2. Previous Issue — Reuse Existing Deadline Engine

**Issue:** The contract created a separate `orders.offer_hold.expire` job handler, duplicating scheduler/retry/audit infrastructure that already exists in `PaymentDeadline`.

**Evidence:** `PaymentDeadline` model has: nullable `assignment` FK, `expire_due()` with idempotent expiry, `JobService` integration with retry, `AuditService` logging. The `assignment` FK being nullable means a deadline can exist without an assignment.

**Decision:** Extend `PaymentDeadline` with a nullable `order_offer` FK. Add routing in `expire_due()`: if `order_offer_id` is set, call `OrderOfferService.expire_hold()`; else call `AssignmentService.expire()` (existing).

**Contract sections changed:** Section 9.4 (rewritten with compatibility proof), Section 13.2 (added deadline.py and deadline_service.py to modified files), Section 13.3 (removed deadline_service.py from "not modified" list)

**Before behavior:** Separate job engine for offer hold expiry. No shared infrastructure with commission deadlines.

**After behavior:** Single canonical deadline engine. Offer holds and commission deadlines share scheduler, retry, audit, and feature gates.

**Compatibility proof:** 9-point matrix verified (fields, statuses, expiry logic, cascade, scheduler, audit, feature gates, idempotency, payment-success completion). Required change: nullable FK + routing null-check in `expire_due()`.

---

## 3. Previous Issue — REJECTED Semantics

**Issue:** The state machine had a `SELECTED → REJECTED` transition triggered by `select_other()`. This contradicted the policy that a second selection is rejected while a hold is active.

**Evidence:** Section 3.1 had `SELECTED | REJECTED | select_other() | Customer selected a different offer on the same order`. This implied the customer could select a different offer during an active hold.

**Decision:** Remove `SELECTED → REJECTED` transition. REJECTED is now a bulk status set on SUBMITTED offers when another offer is ACCEPTED (post-payment). A second selection attempt is rejected at the `select_offer()` entry point, not as a state transition.

**Contract sections changed:** Section 3.1 (state machine diagram and transition table rewritten), Section 5.3 (confirm_payment now includes bulk REJECTED operation)

**Before behavior:** `select_other()` could transition SELECTED → REJECTED. Implied customer could swap selections during hold.

**After behavior:** `select_offer()` rejects if any offer is already SELECTED. REJECTED is set in bulk by `confirm_payment()` on non-selected SUBMITTED offers after payment success. No `select_other()` transition exists.

---

## 4. Previous Issue — Payment Retry Linkage (RISK-004)

**Issue:** The original contract proposed `OrderOffer.payment_intent` FK (1:1), which cannot safely represent multiple payment attempts. A customer may retry payment after failure, creating a new PaymentIntent each time.

**Evidence:** `PaymentIntentService.create_intent()` is idempotent per `(tenant, idempotency_key)`. A new idempotency_key creates a new intent. The 1:1 FK would leave the offer pointing at the latest intent (possibly FAILED) rather than the successful one.

**Decision:** Reverse the FK direction. Add nullable `order_offer` FK to `PaymentIntent` (1:N). Remove `payment_intent` FK from `OrderOffer`. `confirm_payment()` receives and validates the exact successful `payment_intent_id`.

**Contract sections changed:** Section 2 (OrderOffer model — removed payment_intent FK), new Section 6A (PaymentIntent model change, confirm_payment signature, validation rules, idempotency, race handling), Section 5.3 (confirm_payment transaction boundary updated), Section 13.2 (added payments/models.py to modified files)

**Before behavior:** One OrderOffer points to one PaymentIntent. Retry creates orphaned intents.

**After behavior:** One OrderOffer has many PaymentIntents. confirm_payment validates the exact intent: tenant match, offer ownership, SUCCEEDED status, amount/currency match, no prior successful intent.

---

## 5. Files Changed During This Documentation Task

| File | Nature of Change |
|------|-----------------|
| `mimo change/00_WORK_COMPLETED_TO_DATE.md` | Corrected working-tree status, E2E history, integrity statement |
| `mimo change/01_CHANGE_LEDGER.md` | Corrected CL-007 to reflect actual interruption state |
| `mimo change/02_ARCHITECTURE_DECISION_LOG.md` | Changed ADM-011 status; added ADM-012 for RISK-004 |
| `mimo change/03_FILE_CHANGE_REGISTER.md` | Created (new file); added payments/models.py |
| `mimo change/04_TEST_EXECUTION_LOG.md` | Created (new file) |
| `mimo change/05_OPEN_QUESTIONS_AND_RISKS.md` | Created (new file); normalized risk statuses |
| `mimo change/06_FINAL_CONTRACT_REMEDIATION_REPORT.md` | This file; added RISK-004 resolution |
| `mimo change/07_CONTRACT_DIFF_SUMMARY.md` | Created (new file); will be updated |
| `mimo change/08_FINAL_TASK_VERIFICATION.md` | Created (new file); will be updated |
| `OFFER_MARKETPLACE_IMPLEMENTATION_CONTRACT.md` | Four remediations applied (visibility, deadline, REJECTED, payment retry) |

---

## 6. Files Not Changed

| File | Reason |
|------|--------|
| All `src/apps/**/*.py` files | No production code modified |
| All migration files | No migrations generated |
| All test files | No test files created or modified |
| All existing documentation files | Previous reports preserved as-is |

---

## 7. Open Risks

| Risk | Status |
|------|--------|
| RISK-001: PaymentDeadline compatibility | **RESOLVED_IN_CONTRACT** — implementation verification pending |
| RISK-002: Payment success vs hold expiry race | **RESOLVED_IN_CONTRACT** — concurrency tests pending |
| RISK-003: Marketplace visibility | **RESOLVED_IN_CONTRACT** — discovery and submission tests pending |
| RISK-004: Payment retry linkage | **RESOLVED_IN_CONTRACT** — implementation verification pending |
| RISK-005: Event handler transaction semantics | **KNOWN_LIMITATION** |
| RISK-006: REJECTED bulk operation concurrency | **RESOLVED_IN_CONTRACT** — bulk-locking tests pending |
| RISK-007: Commission workflow compatibility | **RESOLVED_IN_CONTRACT** — regression tests pending |
| RISK-008: Real external integrations | **KNOWN_LIMITATION** |

---

## 8. Final Recommendation

The contract is now internally consistent after the three remediations:
1. Marketplace visibility guard prevents new offers during hold
2. PaymentDeadline reuse eliminates duplicate deadline infrastructure
3. REJECTED semantics are unambiguous (bulk post-payment operation only)

**Implementation approval is recommended** with the following conditions:
- RISK-004 (payment retry linkage) must be resolved during implementation
- All tests must use PostgreSQL (per ADM-007)
- Existing operator-assignment flow must remain functional (per ADM-008)
