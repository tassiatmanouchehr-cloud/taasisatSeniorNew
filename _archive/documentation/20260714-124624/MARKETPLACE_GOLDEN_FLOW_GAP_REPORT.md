# MARKETPLACE GOLDEN FLOW GAP REPORT

**Baseline:** 1632 tests passing, 18/18 E2E steps passing (PostgreSQL)
**Repository commit:** `a5dbaf28703142edaa1d770ea8f3c2a45a12640f`
**Date:** July 13, 2026

---

## Current E2E Flow vs Required Golden Flow

The verified E2E flow (18 steps) follows this path:

```
Customer registers → Elder created → Caregiver registers → Supplier created
→ Order created (PENDING_OPERATOR_REVIEW) → Operator approves → Operator assigns supplier
→ Provider accepts → Execution starts → Provider completes → Customer closes
→ Financial party resolved → Invoice created → Wallet credited → Balance checked
```

The required golden flow follows this path:

```
Customer creates order → All eligible caregivers see it → Caregivers submit
independent price/terms offers → Customer compares offers → Customer selects
one offer → Offer held for 30 minutes → Payment succeeds or fails →
Failed payment leaves order retryable → Successful payment creates funded escrow
→ Provider delivers → Customer approves or disputes → Funds released or refunded
→ Commission allocated → Ledger and balances updated
```

**The two flows diverge at step 6 (order approval).** The current flow has an operator manually approve and assign. The golden flow has caregivers independently discover and submit offers.

---

## Step-by-Step Gap Analysis

---

### STEP 1: Customer Creates an Order

#### Existing Models
- `Order` — `apps/orders/models.py:47` (7 states: PENDING_OPERATOR_REVIEW, NEW, WAITING_SERVICE, IN_PROGRESS, COMPLETED, CANCELLATION_REQUESTED, CANCELLED)
- `ServiceCategory`, `ServiceType` — `apps/orders/models.py:1-46`

#### Existing Services
- `create_public_order()` — `apps/orders/services/order_creation.py` (creates order in PENDING_OPERATOR_REVIEW)
- `create_operator_order()` — same file (creates in NEW or WAITING_SERVICE)

#### Existing URLs/Views/APIs
- `/portal/requests/new/` — 7-step wizard in `apps/portal/views.py`
- No API endpoint for order creation

#### Existing Tests
- `apps/orders/tests/test_order_creation.py` — create_public_order, create_operator_order tested

#### What Is Genuinely Working
Order creation via the customer portal wizard works end-to-end. The order is created with status PENDING_OPERATOR_REVIEW.

#### What Is Missing
Nothing. Order creation is complete.

#### Required Change Type
None — this step is DONE.

#### Runtime Dependency
None (standalone).

---

### STEP 2: All Eligible Caregivers Can See the Order

#### Existing Models
- `MatchRound`, `MatchCandidate` — `apps/matching/models.py` (system-generated candidates, not caregiver-initiated)

#### Existing Services
- `MatchOrchestrator.run()` — `apps/matching/services/match_orchestrator.py:36` (generates candidates from all eligible suppliers)
- `EligibilityService.evaluate()` — `apps/matching/services/eligibility.py` (checks tenant, status, availability, category, verification)
- `DiscoveryService.search()` — `apps/discovery/services/discovery_service.py` (public search, not order-specific)

#### Existing URLs/Views/APIs
- `/provider/assignments/` — shows ASSIGNED orders only (`apps/provider_portal/views.py:141`)
- No view for browsing OPEN/AVAILABLE orders
- No API for order discovery by caregivers

#### Existing Tests
- `apps/matching/tests/` — 6 test files covering eligibility, ranking, orchestrator
- `apps/provider_portal/tests/` — 14 test files, none for order browsing

#### What Is Genuinely Working
Matching engine generates candidates algorithmically. Eligibility evaluation works. But this is operator-triggered, not caregiver-initiated.

#### What Is Missing
1. **No order browsing mechanism for caregivers** — providers can only see orders they are already assigned to
2. **No "available orders" query** — no service that returns unassigned orders to a caregiver
3. **No caregiver-facing UI** for browsing open orders

#### Required Change Type
- New service: `OrderDiscoveryService` — query unassigned orders visible to a caregiver
- New view + template: caregiver portal "Available Orders" page
- Extension of existing model: none needed (Order.status already has NEW/WAITING_SERVICE)

#### Runtime Dependency
Depends on Step 1 (order must exist with status NEW or WAITING_SERVICE).

---

### STEP 3: Caregivers Submit Independent Price and Terms Offers

#### Existing Models
- `MatchCandidate` — has `rank_score`, `score_breakdown` (system-generated, not caregiver-submitted)
- No `Offer`, `Proposal`, or `Bid` model exists anywhere

#### Existing Services
- None for caregiver-submitted offers

#### Existing URLs/Views/APIs
- None

#### Existing Tests
- None

#### What Is Genuinely Working
Nothing. The system has no concept of a caregiver-submitted offer.

#### What Is Missing
1. **New model: `OrderOffer`** — stores caregiver-submitted price, terms, estimated duration, message
2. **New service: `OfferService`** — submit, list, withdraw offers
3. **New view + template** — caregiver "Submit Offer" form on order detail page

#### Required Change Type
- New model: `OrderOffer` (order FK, supplier FK, price, currency, terms text, estimated_duration, status, timestamps)
- New service: `OfferService.submit_offer()`, `.list_offers_for_order()`, `.withdraw_offer()`
- New view: caregiver portal offer submission form
- New tests: offer CRUD, validation, uniqueness (one offer per caregiver per order)

#### Runtime Dependency
Depends on Step 2 (caregiver must see the order).

---

### STEP 4: Customer Compares Offers

#### Existing Models
- None for offer comparison

#### Existing Services
- None

#### Existing URLs/Views/APIs
- None

#### Existing Tests
- None

#### What Is Genuinely Working
Nothing.

#### What Is Missing
1. **New service: `OfferComparisonService`** — aggregates offers for an order, enriches with supplier reputation/completion stats
2. **New view + template** — customer portal "Compare Offers" page showing multiple offers side-by-side
3. **Display enrichment**: supplier reputation score, completed jobs count, verification status

#### Required Change Type
- New service: `OfferComparisonService.get_offers_for_order()` returning enriched ViewModels
- New view + template: customer portal offers comparison page
- Depends on the `OrderOffer` model from Step 3

#### Runtime Dependency
Depends on Step 3 (offers must exist).

---

### STEP 5: Customer Selects One Offer

#### Existing Models
- `MatchCandidate.status` can be SELECTED (`apps/matching/models.py:78`) — but this is an internal audit marker, not a customer action
- `SupplierAssignment` — `apps/booking/models.py` (current path: operator assigns, not customer selects)

#### Existing Services
- `MatchOrchestrator.mark_candidate_selected()` — `apps/matching/services/match_orchestrator.py:146` (audit-only, called by AssignmentService)
- `AssignmentService.assign()` — `apps/booking/services/assignment_service.py:60` (creates SupplierAssignment)

#### Existing URLs/Views/APIs
- None for customer offer selection

#### Existing Tests
- Matching orchestrator tests cover mark_candidate_selected
- Assignment tests cover assign/replace/cancel/expire

#### What Is Genuinely Working
`AssignmentService.assign()` works and creates a SupplierAssignment. But it's triggered by operators, not customers selecting from offers.

#### What Is Missing
1. **New service method or new service: `OfferSelectionService.select_offer()`** — validates offer belongs to order, calls `AssignmentService.assign()` with the offer's supplier, marks the offer as SELECTED
2. **New view + template** — customer portal "Select This Offer" button on comparison page
3. **Integration**: selecting an offer must also start the 30-minute payment deadline (Step 6)

#### Required Change Type
- New service: `OfferSelectionService.select_offer(offer_id, customer_user)`
- New view: customer portal offer selection action
- Wiring: after selection, trigger PaymentDeadlineService.create_for_order()
- Depends on `OrderOffer` model (Step 3) and `AssignmentService` (existing)

#### Runtime Dependency
Depends on Steps 3 and 4 (offers must exist and be visible).

---

### STEP 6: Selected Offer Held for 30 Minutes

#### Existing Models
- `PaymentDeadline` — `apps/commission/models/deadline.py` (created by PaymentDeadlineService)

#### Existing Services
- `PaymentDeadlineService.create_for_order()` — `apps/commission/services/deline_service.py:61` (creates deadline with 30-min TTL)
- `PaymentDeadlineService.expire_due()` — same file, line 174 (cascades to AssignmentService.expire())
- `CommissionConfiguration` — `apps/commission/services/configuration.py:14` (DEFAULT_PAYMENT_DEADLINE_SECONDS = 30*60)

#### Existing URLs/Views/APIs
- None visible to users (deadline is internal)

#### Existing Tests
- `apps/commission/tests/test_deadline_service.py` — deadline creation, extension, expiry tested

#### What Is Genuinely Working
The 30-minute deadline data structure and cascade logic fully exist. The expiry → assignment expire → order reopen cascade is implemented.

#### What Is Missing
1. **Feature gate disabled by default**: `commission.payment_deadline.activation_enabled` defaults to `False` (`configuration.py:38`)
2. **Deadline expiry job not scheduled**: even when deadline is created, the expiry job is only scheduled when activation is enabled
3. **No wiring from offer selection to deadline creation**: current flow creates deadline in AssignmentService.assign(), but the golden flow needs it after customer selects an offer

#### Required Change Type
- Wiring only: enable `commission.payment_deadline.activation_enabled = True` for the tenant
- Wiring only: ensure OfferSelectionService (Step 5) calls PaymentDeadlineService.create_for_order()
- The deadline cascade (expire → AssignmentService.expire → order status reset) already exists

#### Runtime Dependency
Depends on Step 5 (offer must be selected to trigger deadline).

---

### STEP 7: Payment Succeeds or Fails

#### Existing Models
- `PaymentIntent` — `apps/payments/models.py:54` (7 states: CREATED, PENDING, AUTHORIZED, SUCCEEDED, FAILED, CANCELLED, EXPIRED)
- `PaymentAttempt` — same file
- `PaymentCallback` — same file

#### Existing Services
- `PaymentIntentService.create_intent()` — `apps/payments/services/payment_intent_service.py`
- `PaymentIntentService.start_attempt()` — same file
- `PaymentCallbackService.process_callback()` — `apps/payments/services/payment_callback_service.py` (processes provider callback, triggers settlement on SUCCEEDED)

#### Existing URLs/Views/APIs
- `POST /api/v1/payments/intents/` — create intent
- `POST /api/v1/payments/intents/<id>/attempts/` — start attempt
- `POST /api/v1/payments/callbacks/fake/` — fake PSP callback
- `/portal/requests/<id>/financial/pay/` — customer portal pay button

#### Existing Tests
- `apps/payments/tests/` — 7 test files covering intent, callback, settlement orchestration, transitions, concurrency

#### What Is Genuinely Working
Payment intent creation, attempt, and callback processing all work. The FakePaymentProviderAdapter simulates success/failure.

#### What Is Missing
1. **No real PSP adapter** — only FakePaymentProviderAdapter exists
2. **Payment failure does not trigger any order/assignment recovery** — FAILED is terminal, no cascade to reopen order
3. **No retry mechanism** — FAILED PaymentIntent has no outgoing transitions (`transitions.py:14`: "SUCCEEDED/FAILED/CANCELLED/EXPIRED are terminal")

#### Required Change Type
- Extension of existing model: PaymentIntent needs a RETRY state or a new PaymentIntent can be created for the same order
- New service method or new service: on payment failure, trigger deadline expiry or assignment expiry to reopen the order
- The existing PaymentDeadline expiry cascade already handles reopening the order — the gap is that FAILED payment doesn't trigger it

#### Runtime Dependency
Depends on Step 6 (deadline must be active for expiry to cascade).

---

### STEP 8: Failed Payment Leaves the Order Retryable

#### Existing Models
- `Order.status` has NEW and WAITING_SERVICE (reassignment possible)
- `SupplierAssignment.status` has EXPIRED

#### Existing Services
- `AssignmentService.expire()` — `apps/booking/services/assignment_service.py:351` (cancels assignment, resets order)
- `PaymentDeadlineService.expire_due()` — cascades to AssignmentService.expire()

#### Existing URLs/Views/APIs
- `/portal/requests/<id>/` — order detail page (could show retry option)

#### Existing Tests
- Assignment expire tested, deadline expiry cascade tested

#### What Is Genuinely Working
The cascade from deadline expiry → assignment expire → order status reset exists and is tested.

#### What Is Missing
1. **FAILED payment does not trigger deadline expiry** — the FAILED callback path doesn't interact with the deadline system at all
2. **No explicit "retry payment" UI** — customer would need to re-initiate payment from scratch
3. **No wiring from payment failure to order recovery**

#### Required Change Type
- Wiring only: in PaymentCallbackService, when status is FAILED and deadline is active, trigger PaymentDeadlineService.expire_due()
- New view: customer portal "Retry Payment" button that creates a new PaymentIntent for the same order
- The underlying order recovery mechanism (deadline expiry → assignment expire → order reset) already exists

#### Runtime Dependency
Depends on Step 7 (payment must fail).

---

### STEP 9: Successful Payment Creates Funded Escrow

#### Existing Models
- `EscrowRecord` — `apps/finance/models/escrow.py` (PR-B conservation tracking: original = released + refunded + blocked + remaining)
- `EscrowMovement` — same file (immutable audit trail)

#### Existing Services
- `SettlementOrchestrationService.settle_payment_intent()` — `apps/payments/services/settlement_orchestration_service.py:130` (routes to escrow when preservice flag is set)
- `EscrowIntegrationService.handle_preservice_payment_succeeded()` — `apps/commission/services/escrow_integration_service.py:52` (completes deadline, holds in escrow)
- `EscrowService.hold_for_order()` — `apps/finance/services/escrow_service.py:134` (creates HELD EscrowRecord)

#### Existing URLs/Views/APIs
- Internal only (settlement triggered by callback processing)

#### Existing Tests
- EscrowService conservation tests, escrow integration tests, settlement orchestration concurrency test

#### What Is Genuinely Working
The funded escrow creation path is fully implemented end-to-end. When all gates are enabled, payment success → escrow hold works.

#### What Is Missing
1. **Three feature gates disabled by default**:
   - `commission.preservice_payment.enabled = False` (`configuration.py:51`)
   - `commission.escrow_production.enabled = False` (`configuration.py:62`)
   - `commission.payment_deadline.activation_enabled = False` (`configuration.py:38`)
2. **Payment intent not tagged as preservice** — the current flow creates a generic intent, not one with `metadata["financial_core_flow"] == "preservice"`
3. **Pre-service payment not wired to order flow** — `PreServicePaymentService` exists but is only invoked from portal views, not from the automated flow

#### Required Change Type
- Wiring only: enable the three feature gates for the tenant
- Wiring only: ensure OfferSelectionService or AssignmentService creates a preservice-tagged PaymentIntent
- The escrow hold logic, conservation tracking, and audit trail all exist

#### Runtime Dependency
Depends on Steps 5 and 6 (offer selected, deadline active).

---

### STEP 10: Provider Delivers the Service

#### Existing Models
- `ExecutionSession` — `apps/execution/models.py` (7 states: SCHEDULED, IN_PROGRESS, PROVIDER_COMPLETED, CUSTOMER_PENDING, CLOSED, PAUSED, INTERRUPTED)

#### Existing Services
- `ExecutionService.create_session()` — `apps/execution/services/session_service.py:40`
- `ExecutionService.start_session()` — same file, line 100 (with payment guard)
- `ExecutionService.complete_session()` — same file, line 143
- `ExecutionService.close_session()` — same file, line 185 (with objection period)
- `ProviderExecutionService` — `apps/execution/services/provider_actions.py` (ownership-gated start/complete)

#### Existing URLs/Views/APIs
- `/provider/assignments/<id>/start/` — start visit
- `/provider/assignments/<id>/complete/` — complete visit
- `/portal/requests/<id>/` — customer sees status

#### Existing Tests
- 10 execution test files covering session lifecycle, provider actions, payment guard

#### What Is Genuinely Working
Service execution lifecycle (start → complete → close) works end-to-end. The payment guard (`ExecutionPaymentGuardService`) blocks execution start when pre-service payment is required but not held.

#### What Is Missing
1. **Execution evidence/media capture not implemented** — belongs to Module 13 (Document/Media), not started
2. **Execution payment guard blocks start when escrow is required** — this is correct behavior, but requires Step 9 (escrow must be funded before execution can start)

#### Required Change Type
- None for basic execution flow
- Evidence capture is a separate feature (Module 13)

#### Runtime Dependency
Depends on Step 9 (escrow must be funded before execution starts, when escrow is enabled).

---

### STEP 11: Customer Approves or Disputes

#### Existing Models
- `ObjectionPeriod` — `apps/commission/models/objection.py` (5 states: OPEN, CUSTOMER_APPROVED, AUTO_APPROVED, DISPUTED, EXPIRED)
- `Dispute` — `apps/commission/models/dispute.py` (4 states: OPEN, UNDER_REVIEW, RESOLVED, DISMISSED)
- `DisputeLine` — same file
- `DisputeResolution` — same file

#### Existing Services
- `ObjectionPeriodService.start_for_completion()` — `apps/commission/services/objection_service.py:48` (creates period on session close)
- `ObjectionPeriodService.approve_by_customer()` — same file, line 105 (marks approved, triggers release)
- `ObjectionPeriodService.auto_approve_if_due()` — same file, line 145 (auto-approves after deadline)
- `DisputeService.open()` — `apps/commission/services/dispute_service.py` (creates dispute, blocks escrow)
- `DisputeService.resolve()` — same file (resolves with allocation)
- `EscrowService.block_for_dispute()` — `apps/finance/services/escrow_service.py:264`

#### Existing URLs/Views/APIs
- `/portal/requests/<id>/financial/approve/` — customer approve button
- `/portal/requests/<id>/financial/dispute/` — customer dispute form
- `/admin-portal/financial/disputes/` — admin dispute queue
- `/admin-portal/financial/disputes/<id>/resolve/` — admin resolve action

#### Existing Tests
- ObjectionPeriodService tests, DisputeService tests, dispute resolution tests, escrow conservation tests

#### What Is Genuinely Working
The approve/dispute flows are fully implemented in code and portal UI.

#### What Is Missing
1. **Feature gates disabled by default**:
   - `commission.dispute_release.enabled = False` (`configuration.py:80`)
   - `commission.objection.automation_enabled = False` (`configuration.py:72`)
2. **Objection period only starts when Escrow exists** — requires Step 9 (escrow funded)
3. **Auto-approval disabled** — customer must manually approve or the period expires without action

#### Required Change Type
- Wiring only: enable `commission.dispute_release.enabled = True` and `commission.objection.automation_enabled = True`
- The approve/dispute/release/refund logic all exists and is tested

#### Runtime Dependency
Depends on Step 9 (escrow must exist for objection period to start).

---

### STEP 12: Funds Are Released or Refunded

#### Existing Models
- `ReleaseInstruction` — `apps/commission/models/release_instruction.py` (status: READY, CONSUMED, FAILED)
- `RefundInstruction` — `apps/commission/models/refund_instruction.py` (status: PENDING, COMPLETED, FAILED)

#### Existing Services
- `ReleaseInstructionService.create()` — `apps/commission/services/release_instruction_service.py:28` (creates READY instruction, calls EscrowService.apply_release)
- `RefundInstructionService.initiate()` — `apps/commission/services/refund_service.py` (creates PENDING instruction, calls PSP adapter)
- `EscrowService.apply_release()` — `apps/finance/services/escrow_service.py:375` (moves funds within escrow, does NOT credit wallets)
- `EscrowService.apply_refund()` — same file (moves funds within escrow)

#### Existing URLs/Views/APIs
- `/admin-portal/financial/instructions/` — admin view of release/refund instructions
- Customer approve/dispute views trigger release/refund

#### Existing Tests
- ReleaseInstruction tests, RefundInstruction tests, escrow conservation tests, reconciliation tests

#### What Is Genuinely Working
ReleaseInstruction and RefundInstruction creation works. Escrow balance accounting works (conservation equation verified).

#### What Is Missing
1. **ReleaseInstruction is never consumed** — PR-B creates the instruction in READY status but explicitly does NOT credit wallets. The docstring at `release_instruction.py:14` states: "PR-B never credits a wallet from this... PR-C is the only future consumer allowed to transition a ReleaseInstruction from READY to CONSUMED"
2. **RefundInstruction calls FakePaymentProviderAdapter** — no real refund path exists
3. **No multi-party wallet credit** — AllocationCalculator exists but is not wired into the release path

#### Required Change Type
- New service: `ReleaseInstructionConsumer` — consumes READY ReleaseInstructions, calls AllocationCalculator to split, credits platform/company/caregiver wallets
- New service or extension: `RefundInstructionConsumer` — processes PENDING RefundInstructions via real PSP
- These are the "PR-C" boundaries explicitly documented in the model docstrings

#### Runtime Dependency
Depends on Steps 11 (approval must trigger release instruction).

---

### STEP 13: Platform/Company/Caregiver Commission Is Allocated

#### Existing Models
- `CommissionSnapshot` — `apps/commission/models/snapshot.py` (frozen commission state at assignment)
- `AllocationCalculator` — `apps/commission/services/allocation_calculator.py` (deterministic 3-way split)

#### Existing Services
- `AllocationCalculator.allocate()` — `apps/commission/services/allocation_calculator.py:49` (pure function: platform/company/caregiver split)
- `CommissionSnapshotService.create_snapshot_for_order()` — `apps/commission/services/snapshot_service.py` (creates snapshot at assignment)
- `SettlementAdjustmentPipeline.run()` — `apps/payments/services/settlement_adjustments.py:51` (IDENTITY FUNCTION: returns zero commission)

#### Existing URLs/Views/APIs
- None (commission is internal)

#### Existing Tests
- AllocationCalculator conservation tests (9 tests), contract concurrency tests

#### What Is Genuinely Working
AllocationCalculator is implemented and thoroughly tested (conservation property: platform + company + caregiver = 100%). CommissionSnapshot creation exists.

#### What Is Missing
1. **SettlementAdjustmentPipeline returns zero** — `settlement_adjustments.py:56`: `commission_amount=zero`. The pipeline is an identity function.
2. **AllocationCalculator not wired into settlement** — the calculator exists but is never called during settlement or release
3. **CommissionSnapshot not consumed** — snapshots are created at assignment but never read by the settlement or release paths
4. **No real commission rates** — the calculator takes rates as parameters; no rates are configured or seeded

#### Required Change Type
- Wiring only: SettlementAdjustmentPipeline.run() should call AllocationCalculator.allocate() with rates from CommissionSnapshot or CommissionPolicy
- The calculator itself is complete and tested
- Commission rates need to be seeded per tenant

#### Runtime Dependency
Depends on Steps 9 and 12 (escrow release must trigger commission allocation).

---

### STEP 14: Ledger and Balances Are Updated

#### Existing Models
- `LedgerEntry` — `apps/finance/models/ledger.py` (append-only, balanced: debit == credit)
- `Wallet` — `apps/wallet/models.py` (party+currency unique)
- `WalletTransaction` — `apps/wallet/models.py` (append-only, idempotent)

#### Existing Services
- `LedgerService.post_entries()` — `apps/finance/services/ledger_service.py` (balanced posting with tenant consistency)
- `WalletTransactionService.credit()` — `apps/wallet/services/wallet_transaction_service.py` (idempotent credit)
- `WalletTransactionService.debit()` — same file (sufficient funds check)

#### Existing URLs/Views/APIs
- `/portal/payments/` — wallet transaction list
- `/provider/earnings/` — provider earnings summary
- `/api/v1/wallet/balance/` — wallet balance API

#### Existing Tests
- Ledger posting tests, wallet service tests, wallet transaction tests (17+6+7 files), wallet atomicity/concurrency tests, wallet tenant isolation tests

#### What Is Genuinely Working
Ledger posting and wallet operations are fully implemented and thoroughly tested. The current E2E flow (steps 15-17) demonstrates wallet credit working end-to-end.

#### What Is Missing
1. **No multi-party wallet credit** — current flow credits only one wallet (beneficiary). The golden flow requires crediting platform, company, and caregiver wallets separately
2. **Commission revenue line never posted** — `settlement_orchestration_service.py:317`: "Extension point: once a future sprint's adjustment pipeline returns a non-zero commission, a third balancing line is posted here. Sprint 1's pipeline always returns zero, so this branch never executes today."

#### Required Change Type
- Wiring only: once ReleaseInstructionConsumer (Step 12) and AllocationCalculator integration (Step 13) are in place, the existing ledger/wallet infrastructure handles the rest
- No new models or services needed for ledger/wallet itself

#### Runtime Dependency
Depends on Steps 12 and 13 (release instruction consumption and commission allocation).

---

## Summary: Gap Classification

### Category A: Entirely Missing (New Model + New Service + New UI)

| Gap | Step | Models | Services | Views | Tests |
|-----|------|--------|----------|-------|-------|
| Order browsing for caregivers | 2 | None | New: OrderDiscoveryService | New: caregiver portal page | New |
| Caregiver offer submission | 3 | New: OrderOffer | New: OfferService | New: caregiver offer form | New |
| Customer offer comparison | 4 | None | New: OfferComparisonService | New: customer comparison page | New |
| Customer offer selection | 5 | None | New: OfferSelectionService | New: customer selection action | New |
| Release instruction consumption (PR-C) | 12 | None | New: ReleaseInstructionConsumer | None (internal) | New |

### Category B: Exists but Disabled (Wiring Only)

| Gap | Step | What Exists | Gate |
|-----|------|------------|------|
| 30-min payment deadline enforcement | 6 | PaymentDeadlineService, cascade logic | `commission.payment_deadline.activation_enabled = False` |
| Funded escrow on payment success | 9 | EscrowService, EscrowIntegrationService | `commission.preservice_payment.enabled = False`, `commission.escrow_production.enabled = False` |
| Customer approve/dispute | 11 | ObjectionPeriodService, DisputeService | `commission.dispute_release.enabled = False`, `commission.objection.automation_enabled = False` |
| Auto-objection-approval | 11 | ObjectionPeriodService.auto_approve_if_due() | `commission.objection.automation_enabled = False` |

### Category C: Exists but Not Wired (Integration Gap)

| Gap | Step | What Exists | What's Missing |
|-----|------|------------|---------------|
| Payment failure → order retry | 8 | FAILED terminal state, deadline cascade | FAILED callback doesn't trigger deadline expiry |
| Commission allocation in settlement | 13 | AllocationCalculator, SettlementAdjustmentPipeline | Pipeline returns zero, calculator not called |
| Multi-party wallet credit on release | 12 | ReleaseInstruction (READY status), Wallet infrastructure | ReleaseInstruction never consumed |
| Commission snapshot consumption | 13 | CommissionSnapshot created at assignment | Snapshot never read by settlement/release |
| Preservice PaymentIntent tagging | 9 | PreServicePaymentService exists | Not called from automated offer→assign flow |

### Category D: Missing External Integration

| Gap | Step | Impact |
|-----|------|--------|
| Real PSP adapter | 7 | Cannot process real payments |
| Real refund PSP integration | 12 | Cannot process real refunds |

---

## Exact Runtime Dependency Order

For the golden flow to work end-to-end, the following dependency chain must be satisfied:

```
STEP 1: Customer creates order (DONE)
  │
  ▼
STEP 2: Caregivers see available orders
  [NEW: OrderDiscoveryService + caregiver portal page]
  │
  ▼
STEP 3: Caregivers submit offers
  [NEW: OrderOffer model + OfferService + caregiver portal form]
  │
  ▼
STEP 4: Customer compares offers
  [NEW: OfferComparisonService + customer portal page]
  │
  ▼
STEP 5: Customer selects offer
  [NEW: OfferSelectionService + customer portal action]
  ├── Calls AssignmentService.assign() (EXISTS)
  └── Calls PaymentDeadlineService.create_for_order() (EXISTS, needs gate enabled)
  │
  ▼
STEP 6: 30-minute hold enforced
  [WIRING: Enable commission.payment_deadline.activation_enabled]
  ├── Deadline created (EXISTS)
  └── Expiry job scheduled (EXISTS, gated)
  │
  ▼
STEP 7: Payment succeeds or fails
  [WIRING: PaymentIntent must be preservice-tagged]
  ├── SUCCEEDED → Step 9
  └── FAILED → Step 8
  │
  ├── STEP 8: Failed payment → order retryable
  │   [WIRING: FAILED callback triggers deadline expiry]
  │   └── Deadline expires → AssignmentService.expire() → Order resets
  │       └── Back to STEP 2 (caregivers can see order again)
  │
  ▼
STEP 9: Successful payment → funded escrow
  [WIRING: Enable commission.preservice_payment.enabled + commission.escrow_production.enabled]
  ├── PaymentCallbackService processes SUCCEEDED (EXISTS)
  ├── SettlementOrchestrationService routes to escrow (EXISTS, gated)
  ├── EscrowIntegrationService.hold_for_order() (EXISTS)
  └── EscrowRecord created with HELD status (EXISTS)
  │
  ▼
STEP 10: Provider delivers service
  [DONE: ExecutionSession lifecycle works]
  ├── start_session() with payment guard (EXISTS)
  ├── complete_session() (EXISTS)
  └── close_session() → starts objection period (EXISTS, gated)
  │
  ▼
STEP 11: Customer approves or disputes
  [WIRING: Enable commission.dispute_release.enabled]
  ├── APPROVE → ObjectionPeriodService.approve_by_customer() (EXISTS)
  │   └── Creates ReleaseInstruction (EXISTS)
  └── DISPUTE → DisputeService.open() + EscrowService.block_for_dispute() (EXISTS)
      └── Admin resolves → DisputeService.resolve() (EXISTS)
  │
  ▼
STEP 12: Funds released or refunded
  [NEW: ReleaseInstructionConsumer to consume READY instructions]
  ├── Release → AllocationCalculator.split() → credit 3 wallets (CALCULATOR EXISTS, CONSUMER MISSING)
  └── Refund → RefundInstructionService.initiate() → PSP (EXISTS, FAKE ONLY)
  │
  ▼
STEP 13: Commission allocated
  [WIRING: SettlementAdjustmentPipeline calls AllocationCalculator]
  └── Pipeline returns non-zero commission (currently returns zero)
  │
  ▼
STEP 14: Ledger and balances updated
  [DONE: Ledger posting and wallet operations work]
  └── Multi-party wallet credit via WalletTransactionService (EXISTS)
```

---

## Quantified Gap Summary

| Metric | Count |
|--------|-------|
| Steps fully working (DONE) | 4 of 14 (Steps 1, 10, 14, and partially 7) |
| Steps implemented but gated (WIRING) | 5 of 14 (Steps 6, 8, 9, 11, 13) |
| Steps entirely missing (NEW) | 5 of 14 (Steps 2, 3, 4, 5, 12) |
| New models needed | 1 (OrderOffer) |
| New services needed | 5 (OrderDiscoveryService, OfferService, OfferComparisonService, OfferSelectionService, ReleaseInstructionConsumer) |
| New views/templates needed | 4 (caregiver browse, caregiver offer form, customer compare, customer select) |
| Feature gates to enable | 4 (deadline, preservice_payment, escrow_production, dispute_release) |
| New test files needed | ~10 (one per new service + integration tests) |

---

## Critical Path to One Complete Golden Flow

The shortest path to a single working golden flow (customer → offer → payment → escrow → execution → approval → release → commission → wallet) requires:

1. **New model:** `OrderOffer` with order FK, supplier FK, price, terms, status
2. **New services (4):** OrderDiscoveryService, OfferService, OfferComparisonService, OfferSelectionService
3. **New views (4):** caregiver browse, caregiver submit, customer compare, customer select
4. **Wiring (4 feature gates):** deadline, preservice_payment, escrow_production, dispute_release
5. **Wiring (1 integration):** FAILED payment → deadline expiry cascade
6. **New service (1):** ReleaseInstructionConsumer (PR-C: consume READY instructions, call AllocationCalculator, credit wallets)
7. **Wiring (1):** SettlementAdjustmentPipeline calls AllocationCalculator instead of returning zero
8. **Tests (~10 files):** covering new models, services, views, and integration paths

**Estimated effort:** The 4 feature gates can be enabled in minutes. The 4 new services + 1 model + 4 views + 1 consumer represent the bulk of the work. The existing infrastructure (ledger, wallet, escrow, deadline cascade, objection period, dispute resolution) is already built and tested.
