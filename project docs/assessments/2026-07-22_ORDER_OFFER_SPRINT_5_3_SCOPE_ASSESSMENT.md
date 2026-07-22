# ORDER OFFER SPRINT 5.3 SCOPE ASSESSMENT

**Date:** 2026-07-22
**Repository HEAD:** `f0801d7` (main, post-PR #44 Sprint 5.2 merge)
**Assessor:** Kiro
**Status:** Immutable assessment — do not edit after approval

---

## 1. Executive Summary

Sprint 5.3 is the final domain-logic sprint for the OrderOffer lifecycle. It implements `accept_offer()` (SELECTED → ACCEPTED, crossing into booking/assignment/financial domains) and `cancel_offers_for_order()` (bulk-cancel active offers when an order is cancelled). A prerequisite cancellation-authorization remediation is recommended as a separate, preceding PR but is not strictly blocking due to zero production call sites for the unprotected functions.

**Recommended scope:** Sprint 5.3A (prerequisite: cancellation authorization fix) + Sprint 5.3B (`accept_offer` + `cancel_offers_for_order`).

---

## 2. Current Repository State

| Metric | Value |
|---|---|
| Main HEAD | `f0801d7` |
| Sprint 5.1 | MERGED (PR #41) — submit, edit, withdraw |
| Sprint 5.2 | MERGED (PR #44) — select, expire |
| Full regression | 2,578/2,578 PASS (CI) |
| OrderOffer selection tests | 32 |
| OrderOffer service tests | 29 |
| OrderOffer model tests | 40 |
| Architecture guardrail tests | 28 |
| Concurrency test files | 13 |

---

## 3. Current State Machine

### Implemented Transitions

| From | Action | To | Sprint |
|---|---|---|---|
| — | `submit_offer` | SUBMITTED | 5.1 |
| SUBMITTED | `edit_offer` | SUBMITTED (fields) | 5.1 |
| SUBMITTED | `withdraw_offer` | WITHDRAWN | 5.1 |
| SUBMITTED | `select_offer` | SELECTED | 5.2 |
| SUBMITTED | (competing, side-effect) | REJECTED | 5.2 |
| SELECTED | `expire_held_offers` | EXPIRED | 5.2 |

### Missing Transitions (Sprint 5.3 Candidates)

| From | Action | To | Sprint |
|---|---|---|---|
| SELECTED | `accept_offer` | ACCEPTED | **5.3** |
| SUBMITTED or SELECTED | `cancel_offers_for_order` | CANCELLED | **5.3** |

### Transitions That Must Never Occur

- Any terminal status → any other status (OFFER_TERMINAL_STATUSES enforced by service)
- SUBMITTED → ACCEPTED (must pass through SELECTED first)
- SELECTED → SUBMITTED (no de-selection mechanism)
- Any terminal → re-activation (UniqueConstraint prevents re-submission)

---

## 4. `accept_offer` Assessment

### 4.1 Existence Check

**Does NOT exist** in the codebase. Confirmed by repository-wide search. The `OrderOfferService` docstring explicitly states: "Future sprints: accept, cancel."

### 4.2 Design (from approved State Machine Review §5 and §6)

| Dimension | Determination |
|---|---|
| **Actor** | Customer (order owner) |
| **Permission key** | None required — ownership is the boundary (consistent with select_offer) |
| **Source state** | Offer: SELECTED with `hold_active == True` |
| **Target state** | Offer: ACCEPTED (terminal) |
| **Order status after** | WAITING_SERVICE (via `status_machine.assign_supplier()`) |
| **Supplier verification** | Offer's supplier must still be ACTIVE at acceptance time |
| **Ownership rule** | `_verify_order_ownership()` — same dual-path as select_offer |
| **Tenant isolation** | Inherited from offer/order (invariant from submission) |
| **Row locks** | Offer row (verify hold_active) → Order row (for assign_supplier) |
| **Idempotency** | Already-ACCEPTED → error |
| **Audit event** | `orders.offer.accepted` |
| **Assignment** | Calls `status_machine.assign_supplier(order_id, supplier)` |
| **Booking** | `AssignmentService.assign()` creates SupplierAssignment + opens financial core |
| **Financial** | CommissionSnapshot, PaymentDeadline, optionally PreServicePayment (all via AssignmentService) |
| **Notifications** | ORDER_ASSIGNED domain event (via AssignmentService) triggers notification handler |
| **Concurrency** | Accept vs. expire race: `select_for_update` on offer row, verify `hold_active` under lock |
| **Rollback** | If `assign_supplier()` or `AssignmentService.assign()` raises, entire transaction rolls back — offer stays SELECTED |
| **Schema changes** | None — `OrderOfferStatus.ACCEPTED` and all fields already exist |

### 4.3 Domain Boundary Decision

**Critical question:** Should `accept_offer()` call `status_machine.assign_supplier()` directly, or go through `AssignmentService.assign()`?

**Answer (from repository evidence):**

`AssignmentService.assign()` is the canonical orchestration layer. It:
1. Calls `status_machine.assign_supplier()` (sole Order mutator)
2. Creates `SupplierAssignment` record (versioned history)
3. Opens financial core (CommissionSnapshot, PaymentDeadline, PreServicePayment)
4. Publishes domain events (ORDER_ASSIGNED)
5. Requires `BOOKING_ASSIGNMENT_ASSIGN` permission — but can accept `ownership_authorized_by` for customer-authorized actions

**Recommendation:** `accept_offer()` should call `AssignmentService.assign()` with `ownership_authorized_by=actor` (the customer) and `assignment_source=AssignmentSource.MANUAL` (or a new `OFFER_ACCEPTANCE` source if we want traceability). This avoids duplicating financial-core wiring inside the offer service.

### 4.4 Lock Ordering (Different from select_offer)

- **select_offer**: Order row first → offer row → competing offers
- **accept_offer**: Offer row first (verify hold) → calls `AssignmentService.assign()` which locks Order row internally

This is the REVERSE of select_offer's lock ordering. The reason: accept needs to verify the offer's hold status before touching the order, whereas select needs to verify order status before touching offers.

**Deadlock risk:** Low. accept_offer locks a specific offer row then the order row. select_offer locks the order row then offer rows. A deadlock requires a concurrent select and accept on the same order — but once an offer is SELECTED, no other offer can be selected (UniqueConstraint), and the same customer is unlikely to be selecting and accepting simultaneously. The `select_for_update` with no timeout is safe here.

---

## 5. `cancel_offers_for_order` Assessment

### 5.1 Existence Check

**Does NOT exist** in the codebase. Confirmed by repository-wide search.

### 5.2 Design

| Dimension | Determination |
|---|---|
| **When it runs** | As a side-effect when `approve_cancellation()` transitions an order to CANCELLED |
| **Actor** | System (cascading from order cancellation) |
| **Cancellable statuses** | SUBMITTED, SELECTED (all non-terminal / `is_active == True`) |
| **Whether accepted offers may be cancelled** | **NO** — ACCEPTED is terminal; an accepted order should never be cancelled through this path (it's already assigned) |
| **Target status** | CANCELLED (distinct from REJECTED, EXPIRED, WITHDRAWN) |
| **Public or internal** | Internal orchestration helper called by order-cancellation logic — NOT a standalone public API |
| **Idempotency** | Fully idempotent — skips terminal offers |
| **Row locking** | Per-offer `select_for_update()` within the cancellation transaction |
| **Module ownership** | Belongs in `OrderOfferService` (sole writer for offer state) |
| **Audit** | `orders.offer.cancelled` per offer (with cancellation initiator as actor) |
| **Notification** | None (order-level cancellation notification is separate) |

### 5.3 Semantic Distinction Among Terminal States

| Status | Cause | Actor | Reversible |
|---|---|---|---|
| REJECTED | Customer selected a different offer | System (side-effect) | No |
| EXPIRED | 30-minute hold timed out | System (background) | No |
| WITHDRAWN | Supplier voluntarily pulled their offer | Supplier | No |
| **CANCELLED** | Parent order was cancelled while offer was active | System (cascading) | No |
| ACCEPTED | Customer accepted during active hold | Customer | No |

Each status represents a distinct, semantically meaningful terminal condition. `CANCELLED` is specifically "order-level cancellation propagated to this offer."

### 5.4 Wiring Decision

`cancel_offers_for_order()` should be called from within `approve_cancellation()` (in `status_machine.py`) AFTER the order status transitions to CANCELLED, within the same `@transaction.atomic` block. This ensures:
- All active offers are cancelled atomically with the order
- No race: a concurrent `select_offer` call would fail because order is no longer in NEW status (the order row lock serializes them)

---

## 6. Cancellation Permission-Gap Assessment

### 6.1 Evidence

From `status_machine.py`:

```python
@transaction.atomic
def request_cancellation(*, order_id, requested_by, reason=""):
    order = Order.objects.select_for_update().get(id=order_id)
    _ensure_not_final(order)
    # ... NO PermissionService.require() call ...
```

```python
@transaction.atomic
def approve_cancellation(*, order_id, changed_by=None):
    order = Order.objects.select_for_update().get(id=order_id)
    # ... NO PermissionService.require() call; changed_by defaults to None ...
```

### 6.2 Severity Assessment

| Factor | Finding |
|---|---|
| Production call sites (views/APIs) | **ZERO** — no portal or API currently calls either function |
| Test call sites | 3 (in `test_orders.py`) |
| Seed/dev call sites | 1 (`seed_product_walkthrough.py`) |
| UUID guessability | Practically impossible (UUIDv4) |
| Current exploitability | **None** — no production endpoint exposes these functions |

### 6.3 Classification

**Architectural inconsistency** — a latent authorization gap that would become exploitable the moment any view/API wires these functions without adding its own permission check.

**NOT a confirmed security defect today** — because no production path reaches these functions.

### 6.4 Is it a Sprint 5.3 Prerequisite?

**Strict answer:** No, because:
- `accept_offer()` does not call cancellation functions
- `cancel_offers_for_order()` is an internal helper called BY the cancellation path, not calling INTO it
- The race "order cancelled during accept" is handled by Order row locking

**Pragmatic recommendation:** Fix it as Sprint 5.3A (a small, isolated, preceding PR) because:
- It's only ~20 lines of code + 2 new permission keys + 4 tests
- It demonstrates good security hygiene before adding `cancel_offers_for_order`
- Any future developer wiring cancellation into a view will find it already protected
- It makes the sprint boundary cleaner

### 6.5 Required Remediation

1. Register `orders.cancellation.request` and `orders.cancellation.approve` permission keys
2. Add `PermissionService.require()` calls to both functions
3. Add `tenant_id` parameter for proper scoping (currently the order is fetched without tenant filter)
4. Add 4 tests: authorized request, unauthorized request, authorized approve, unauthorized approve
5. Update existing tests if they break (unlikely — tests use the functions directly, not via views)

---

## 7. Domain-Boundary Analysis

### accept_offer Calls

```
OrderOfferService.accept_offer()
  ├─ OrderOffer row lock (verify hold_active)
  ├─ Offer status → ACCEPTED
  ├─ AuditService.log("orders.offer.accepted")
  └─ AssignmentService.assign()
       ├─ Order row lock
       ├─ PermissionService.require(BOOKING_ASSIGNMENT_ASSIGN, ownership_authorized_by=actor)
       ├─ status_machine.assign_supplier() → Order.status → WAITING_SERVICE
       ├─ SupplierAssignment.objects.create()
       ├─ EventPublisher.publish("Booking.Assignment.Created.v1")
       ├─ publish_domain_event(ORDER_ASSIGNED) → on_commit
       └─ _open_financial_core_for_assignment()
            ├─ CommissionSnapshotService.create_snapshot_for_order()
            ├─ PaymentDeadlineService.create_for_order()
            └─ PreServicePaymentService (if enabled)
```

### cancel_offers_for_order Calls

```
status_machine.approve_cancellation()
  ├─ Order.status → CANCELLED
  └─ OrderOfferService.cancel_offers_for_order()
       ├─ OrderOffer.objects.filter(order=order, status__in=active_statuses)
       ├─ Per-offer select_for_update()
       ├─ offer.status → CANCELLED
       └─ AuditService.log("orders.offer.cancelled")
```

### What Each Service MUST NOT Own

| Service | Must Not |
|---|---|
| OrderOfferService | Create SupplierAssignment, mutate Order.status directly, open financial core |
| AssignmentService | Mutate OrderOffer status, know about offer selection/expiry |
| status_machine | Mutate OrderOffer status (except indirectly via cancel_offers_for_order wiring) |
| Notifications | Any — handled via domain events, not direct calls |

---

## 8. Concurrency and Invariant Analysis

| Invariant | Protection Mechanism |
|---|---|
| At most one ACCEPTED offer per order | DB: `uq_order_offer_one_selected_per_order` prevents two SELECTED; service: only SELECTED → ACCEPTED; transitivity ensures at most one ACCEPTED |
| Accepted offer must belong to the order | Service: `offer.order_id == order.id` (verified via query) |
| Only SELECTED, non-expired offers may be accepted | Service: `offer.status == SELECTED` + `hold_active == True` under lock |
| An expired hold cannot be accepted | Service: `hold_expires_at > now()` check under `select_for_update` |
| An order cannot accept two offers concurrently | DB constraint (one SELECTED) + service transition (SELECTED → ACCEPTED atomically) |
| Order cancellation cannot leave active offers | `cancel_offers_for_order()` within same transaction as `approve_cancellation()` |
| Accepted/assigned orders cannot be cancelled through wrong pathway | `_ensure_not_final()` prevents cancellation of COMPLETED; accept moves to WAITING_SERVICE which is still cancellable by design |
| Repeated calls remain safe | `accept_offer`: ACCEPTED is terminal → error on re-call; `cancel_offers_for_order`: skips terminal offers |

---

## 9. Test-Gap Analysis

### Existing Tests (Sprint 5.2 already covers)

- ✅ Select offer (happy path, authorization, concurrency, state validation)
- ✅ Expire held offers (expiry, idempotency, batch, tenant scoping)
- ✅ Order cancellation lifecycle (request → approve → final state)
- ✅ Assignment lifecycle (assign → start → complete)
- ✅ Final state immutability (cannot assign/start/complete after cancel)

### Missing Tests Required for Sprint 5.3

**accept_offer (~12-15 tests):**
- Happy path: SELECTED + hold_active → ACCEPTED + Order → WAITING_SERVICE + SupplierAssignment created
- Expired hold rejected (hold_expires_at < now())
- Non-SELECTED offer rejected (wrong status)
- Non-owner cannot accept (authorization)
- Cross-tenant reject
- None actor rejected
- Order already assigned (edge case — should not happen with proper state machine)
- Concurrent accept vs expire race (TransactionTestCase)
- Audit event recorded
- Financial core opened (CommissionSnapshot, PaymentDeadline exist)
- Domain event published (ORDER_ASSIGNED)
- Supplier ACTIVE re-verification at accept time
- Already-ACCEPTED → error (idempotency)

**cancel_offers_for_order (~8-10 tests):**
- Cancels SUBMITTED offers
- Cancels SELECTED offers
- Skips terminal offers (already WITHDRAWN, REJECTED, EXPIRED, ACCEPTED)
- Idempotent (double call safe)
- Cancels all active offers in one order (batch)
- Does not affect other orders' offers
- Audit recorded per cancelled offer
- Wired into approve_cancellation (integration)

**Cancellation authorization remediation (~4 tests):**
- Unauthorized user cannot request cancellation
- Unauthorized user cannot approve cancellation
- Authorized user can request
- Authorized user can approve

### Test Type Distribution

| Category | Count | Type |
|---|---|---|
| accept_offer unit/service | 12-15 | TestCase |
| accept_offer concurrency | 1 | TransactionTestCase |
| cancel_offers_for_order | 8-10 | TestCase |
| Cancellation auth remediation | 4 | TestCase |
| **Total new** | **25-30** | — |

---

## 10. Migration Assessment

**No migration required.**

All model fields for acceptance already exist in `0008_orderoffer.py`:
- `OrderOfferStatus.ACCEPTED` enum value
- `OrderOfferStatus.CANCELLED` enum value
- `OFFER_TERMINAL_STATUSES` includes both

All `Order` model fields for assignment already exist:
- `assigned_supplier` FK
- `status` field

`SupplierAssignment` model is fully defined in `booking/0001_initial.py`.

The pre-existing `kernel` app migration drift (RISK-009 / RM-001) remains **out of scope** and unchanged.

---

## 11. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| accept_offer crosses into booking/financial — larger blast radius | Medium | Call AssignmentService.assign() (tested, proven); don't duplicate financial wiring |
| Cancellation permission gap | Low (today) | Fix as Sprint 5.3A prerequisite |
| Lock ordering difference between select and accept | Low | Different call paths; documented deadlock analysis shows low risk |
| Financial-core failure during accept | Medium | Transaction rollback — offer stays SELECTED, can retry |
| accept vs expire race | Medium | Offer row locked first; expire uses skip_locked (safe) |
| cancel_offers_for_order wiring into status_machine | Low | Tight coupling, but architecturally correct (same transaction) |

---

## 12. Recommended Sprint 5.3 Scope

### Sprint 5.3A — Cancellation Authorization Remediation (prerequisite, separate PR)

**Scope:**
1. Register `orders.cancellation.request` + `orders.cancellation.approve` permission keys
2. Add `PermissionService.require()` to `request_cancellation()` and `approve_cancellation()`
3. Add `tenant_id` parameter for proper scoping
4. 4 new tests

**Estimated size:** ~50 lines of production code + ~80 lines of tests

### Sprint 5.3B — accept_offer + cancel_offers_for_order (main feature PR)

**Scope:**
1. `OrderOfferService.accept_offer(*, offer_id, actor, tenant_id)` — SELECTED → ACCEPTED + assignment
2. `OrderOfferService.cancel_offers_for_order(*, order, actor=None)` — bulk-cancel active offers
3. Wire `cancel_offers_for_order` into `approve_cancellation()` in `status_machine.py`
4. ~25-30 new tests
5. Documentation synchronization

**Estimated size:** ~150 lines of production code + ~500 lines of tests

---

## 13. Explicit Exclusions

| Exclusion | Reason |
|---|---|
| Views/URLs/API endpoints | Service layer must be complete first |
| Background scheduler for expiry | Infrastructure, not domain logic |
| Real SMS/payment provider | Unrelated integration |
| Invoice workflow (Phase 6) | Depends on Phase 5 completion |
| Financial engine review (Phase 7) | Depends on Phases 5-6 |
| Kernel migration drift (RM-001) | Unrelated maintenance item |
| Customer de-selection | Unresolved business decision |
| Admin force-accept/expire | Future feature |

---

## 14. Recommended Implementation Order

1. **Sprint 5.3A** (separate PR, merge first):
   - Register cancellation permission keys
   - Add PermissionService.require() to request_cancellation/approve_cancellation
   - Add tenant_id parameter
   - Tests
   - Documentation sync

2. **Sprint 5.3B** (main feature PR):
   - Implement `cancel_offers_for_order()` (simpler, no cross-domain)
   - Wire into `approve_cancellation()`
   - Test cancel_offers_for_order independently
   - Implement `accept_offer()` (complex, cross-domain)
   - Test accept_offer independently
   - Integration test: full lifecycle submit → select → accept → assigned
   - Documentation sync

---

## 15. GO / NO-GO

### **GO** (with Sprint 5.3A prerequisite)

| Condition | Status |
|---|---|
| Model ready (ACCEPTED, CANCELLED statuses, all fields) | ✅ |
| No migration needed | ✅ |
| Service patterns established (Sprint 5.1 + 5.2) | ✅ |
| Assignment integration proven (AssignmentService tested) | ✅ |
| Concurrency strategy proven (UniqueConstraint + locks) | ✅ |
| Authorization model clear (ownership for accept, system for cancel) | ✅ |
| Financial core integration path proven (AssignmentService._open_financial_core) | ✅ |
| Cancellation gap low severity (no production exposure) | ✅ |
| Sprint 5.3A is small and isolatable | ✅ |
| Cross-domain boundary well-defined (offer → AssignmentService → financial) | ✅ |

**Recommendation:** Proceed with Sprint 5.3A immediately (cancellation auth fix), then Sprint 5.3B upon its merge.
