# OPEN QUESTIONS AND RISKS

**Repository:** taasisatSenior
**Session:** Offer Marketplace Analysis and Contract Development

---

## Status Categories

| Status | Meaning |
|--------|---------|
| OPEN | Unresolved architecture or product decision |
| RESOLVED_IN_CONTRACT | Design decision completed, implementation not yet verified |
| VERIFIED_IN_IMPLEMENTATION | Implemented and tested |
| KNOWN_LIMITATION | Accepted and outside current scope |

---

## RISK-001: PaymentDeadline Compatibility for Offer Hold

```
Risk ID: RISK-001
Description: PaymentDeadline.expire_due() currently calls AssignmentService.expire() unconditionally.
             For offer holds, it must call OrderOfferService.expire_hold() instead.
             Adding a nullable order_offer FK changes the model schema.
Evidence: deadline_service.py line 212: AssignmentService.expire(order_id=deadline.order_id, ...)
          deadline.py: assignment FK is nullable (SET_NULL), order FK is PROTECT
Impact: If the expiry routing is incorrect, offer holds may not expire or may incorrectly expire assignments
Probability: Low — the change is additive (nullable FK) and the routing is a simple null-check
Mitigation: Add order_offer FK as nullable. In expire_due(), check: if deadline.order_offer_id is set, call OrderOfferService.expire_hold(); else call AssignmentService.expire() (existing behavior)
Decision required: Contract must specify exact expiry routing logic
Owner: Implementation team
Status: RESOLVED_IN_CONTRACT — implementation verification pending
```

## RISK-002: Race Between Payment Success and Hold Expiry

```
Risk ID: RISK-002
Description: Payment may succeed at the exact moment the 30-minute hold expires.
             Two concurrent operations: PaymentCallbackService.process_callback() and
             PaymentDeadlineService.expire_due().
Evidence: process_callback() uses transaction.atomic() with PaymentIntent row lock.
          expire_due() uses select_for_update() on PaymentDeadline.
          These lock different rows — no mutual exclusion.
Impact: Double-transition: offer could become both ACCEPTED and EXPIRED
Probability: Very low (single-digit millisecond window, no production traffic)
Mitigation: OrderOfferService.confirm_payment() and expire_hold() both use select_for_update() on OrderOffer.
            The second operation sees the offer already in a terminal state and becomes a no-op.
Decision required: Confirm that OrderOffer locking serializes these two paths
Owner: Implementation team
Status: RESOLVED_IN_CONTRACT — concurrency tests pending
```

## RISK-003: Marketplace Visibility During Active Hold

```
Risk ID: RISK-003
Description: Order stays NEW during hold, but must not appear as freely available.
             Discovery query must exclude orders with a SELECTED offer.
Evidence: OrderDiscoveryService (new) must add: NOT EXISTS (SELECT 1 FROM orders_orderoffer WHERE order_id=orders_order.id AND status='selected')
Impact: If the guard is missing, other caregivers may submit offers on a held order
Probability: None if guard is implemented, high if forgotten
Mitigation: Contract specifies discovery query guard. Service tests verify exclusion.
Decision required: None — addressed in Remediation 1
Owner: Implementation team
Status: RESOLVED_IN_CONTRACT — discovery and submission tests pending
```

## RISK-004: Payment Retry Linkage to Multiple PaymentIntents

```
Risk ID: RISK-004
Description: Customer may create multiple PaymentIntents for the same order during retries.
             Each intent is independent. The offer's payment_intent FK points to the LATEST intent.
             A single OrderOffer.payment_intent FK cannot safely represent multiple attempts.
Evidence: PaymentIntentService.create_intent() is idempotent per (tenant, idempotency_key).
          A new idempotency_key creates a new intent.
Impact: If the offer links to an old FAILED intent, confirm_payment() may not find the SUCCEEDED intent
Mitigation: RESOLVED IN CONTRACT — see Section 5.3 and Section 6A below.
            PaymentIntent gains nullable order_offer FK. confirm_payment() receives and validates
            the exact successful PaymentIntent. Multiple validation checks prevent stale/wrong/cross-tenant intents.
Decision required: None — design completed in this remediation
Owner: Implementation team
Status: RESOLVED_IN_CONTRACT — implementation verification pending
```

## RISK-005: Event Handler Transaction Semantics

```
Risk ID: RISK-005
Description: DomainEvent handlers run AFTER the transaction commits (via transaction.on_commit).
             If a handler fails, the event is lost (no retry).
Evidence: publisher.py: handlers are invoked in a for-loop with try/except that logs but does not re-raise.
          The event is already audited before handlers run.
Impact: Notification delivery failure is silent — no retry, no dead-letter
Probability: Medium — fake providers may fail under load
Mitigation: Acceptable for current implementation. Real providers (PR-C scope) need retry.
Decision required: None for this epic — documented limitation
Owner: Future PR-C scope
Status: KNOWN_LIMITATION
```

## RISK-006: REJECTED Semantics After Payment Success

```
Risk ID: RISK-006
Description: After payment succeeds, non-selected SUBMITTED offers must transition to REJECTED.
             This is a bulk status update that must not conflict with concurrent caregiver edits.
Evidence: confirm_payment() must update all SUBMITTED offers for the same order.
          A caregiver may be editing/withdrawing an offer concurrently.
Impact: Concurrent edit/withdraw may see stale data or fail with IntegrityError
Mitigation: Use select_for_update on OrderOffer rows during the bulk update.
            Caregiver edit/withdraw acquires its own lock and retries on conflict.
Decision required: Contract must specify lock ordering for bulk REJECTED transition
Owner: Implementation team
Status: RESOLVED_IN_CONTRACT — bulk-locking tests pending
```

## RISK-007: Existing Commission Workflow Compatibility

```
Risk ID: RISK-007
Description: Adding order_offer FK to PaymentDeadline must not break existing commission deadline behavior.
          The existing flow: AssignmentService.assign() → PaymentDeadlineService.create_for_order()
          creates a deadline WITH an assignment FK. The new flow creates a deadline WITHOUT assignment FK.
Evidence: deadline.py: assignment FK is nullable (SET_NULL). expire_due() calls
          AssignmentService.expire(order_id=deadline.order_id) — uses order_id, not assignment_id.
Impact: If expire_due() assumes assignment always exists, it may fail for offer-hold deadlines
Mitigation: expire_due() already uses deadline.order_id, not deadline.assignment_id.
            The only change needed is routing: check deadline.order_offer_id to decide which expire path.
Decision required: Verify expire_due() does not reference deadline.assignment_id in its cascade
Owner: Implementation team
Status: RESOLVED_IN_CONTRACT — regression tests pending
```

## RISK-008: Real External Integration Gaps

```
Risk ID: RISK-008
Description: All external integrations are fake. The Offer Marketplace will be tested against fake providers.
Evidence: FakePaymentProviderAdapter, FakeSmsProvider, FakeEmailProvider, FakePushProvider, FakeInAppProvider
Impact: E2E tests prove code correctness but not production readiness
Probability: Certain — by design
Mitigation: Documented limitation. Real integrations are separate epics.
Decision required: None — out of scope
Owner: Future sprints
Status: KNOWN_LIMITATION
```

## RISK-009: Pre-existing accounts/kernel Cosmetic Migration Drift

```
Risk ID: RISK-009
Description: makemigrations --check reports cosmetic Alter field changes for accounts (7 changes)
             and kernel (50+ changes) on every run. These are Django version-skew artifacts.
Evidence: makemigrations --check exits with code 1; no real schema changes.
Impact: Developers may be confused by phantom migration proposals. Must not create these migrations.
Mitigation: Documented as known cosmetic drift. manage.py migrate always reports "no migrations to apply".
Decision required: None — documented, non-blocking
Owner: Future maintenance
Status: KNOWN_LIMITATION
```

## RISK-010: Pre-existing seed_test_product_walkthrough order_number Collision

```
Risk ID: RISK-010
Description: test_seed_product_walkthrough.py occasionally fails with IntegrityError on order_number
             uniqueness. The order_number auto-generation (ORD-YYYYMMDD-XXXX with random 4-digit suffix)
             can collide when two orders are created in the same second.
Evidence: Full regression suite error in Run 010: IntegrityError on order_number.
Impact: Test flakiness — not related to OrderOffer model or Phase 1 changes.
Mitigation: Known pre-existing issue. Not blocking for Phase 1 merge. Should be fixed separately.
Decision required: None — pre-existing, not Phase 1 scope
Owner: Existing seed command maintainer
Status: KNOWN_LIMITATION
```

## RISK-011: No Phase 1 Architecture Blocker

```
Risk ID: RISK-011
Description: Phase 1 implementation has been reviewed, remediated, and verified.
Evidence: 40 OrderOffer tests pass, 119 Orders tests pass, 1671/1672 regression tests pass
          (1 pre-existing seed error), single migration, canonical constraint in place.
Impact: None — Phase 1 is complete.
Mitigation: None needed.
Decision required: None
Owner: Architecture authority
Status: RESOLVED_IN_CONTRACT — implementation verified
```
