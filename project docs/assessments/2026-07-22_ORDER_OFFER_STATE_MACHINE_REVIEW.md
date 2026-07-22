# ORDER OFFER STATE MACHINE — FINAL PRE-IMPLEMENTATION DESIGN REVIEW

**Date:** 2026-07-22
**Repository HEAD:** `8910a7c` (main)
**Status:** Immutable assessment — do not edit after approval

---

## 1. Repository Baseline

| Metric | Value |
|---|---|
| Main HEAD | `8910a7c` |
| Sprint 5.1 | MERGED (PR #41) |
| Implemented methods | `submit_offer`, `edit_offer`, `withdraw_offer` |
| OrderOffer service tests | 29 |
| Full regression | 2,546/2,546 PASS (CI) |
| DB constraints | `uq_order_offer_one_per_supplier`, `uq_order_offer_one_selected_per_order` |

## 2. Evidence Sources

| Source | Path | Purpose |
|---|---|---|
| Model | `src/apps/orders/models.py` | OrderOfferStatus enum, model fields, properties, constraints |
| Service | `src/apps/orders/services/order_offer_service.py` | Current implementation (submit/edit/withdraw) |
| Status machine | `src/apps/orders/services/status_machine.py` | Order state transitions, cancellation functions |
| Assignment | `src/apps/booking/services/assignment_service.py` | How supplier assignment works |
| Permissions | `src/apps/kernel/permissions/keys.py` | Registered permission keys |
| Migration | `src/apps/orders/migrations/0008_orderoffer.py` | DB schema and constraints |
| Tests | `src/apps/orders/tests/test_order_offer_service.py` | 29 test methods |
| Architecture assessment | `project docs/assessments/2026-07-21_*` | Original lifecycle design |
| Sprint 5.2 scope assessment | `project docs/assessments/2026-07-22_*_SCOPE_*` | Prior scope analysis |

## 3. Existing Status Inventory (from `OrderOfferStatus` enum)

| Status | Value | Active? | Terminal? |
|---|---|---|---|
| SUBMITTED | `"submitted"` | Yes | No |
| SELECTED | `"selected"` | Yes | No |
| ACCEPTED | `"accepted"` | No | **Yes** |
| EXPIRED | `"expired"` | No | **Yes** |
| WITHDRAWN | `"withdrawn"` | No | **Yes** |
| REJECTED | `"rejected"` | No | **Yes** |
| CANCELLED | `"cancelled"` | No | **Yes** |

**Active states** (from model `is_active` property): SUBMITTED, SELECTED
**Terminal states** (from `OFFER_TERMINAL_STATUSES`): ACCEPTED, EXPIRED, WITHDRAWN, REJECTED, CANCELLED

## 4. Status Semantics

### SUBMITTED
- **Meaning:** Supplier has submitted a price/terms offer; awaiting customer decision
- **Active:** Yes
- **Edit allowed:** Yes (`can_edit` property)
- **Withdraw allowed:** Yes (`can_withdraw` property)
- **Customer selection allowed:** Yes (`can_select` property)
- **Supplier acceptance/rejection:** N/A (supplier is the submitter, not the selector)
- **Automated expiration:** No
- **Affects competing offers:** No
- **Affects parent order:** No

### SELECTED
- **Meaning:** Customer has chosen this offer; a 30-minute hold is active
- **Active:** Yes
- **Edit allowed:** No (status ≠ SUBMITTED)
- **Withdraw allowed:** No (status ≠ SUBMITTED)
- **Customer selection allowed:** No (already selected)
- **Acceptance allowed:** Yes (if `hold_active` — hold not expired)
- **Automated expiration:** Yes (when `hold_expires_at < now()`)
- **Affects competing offers:** All other SUBMITTED offers were REJECTED at selection time
- **Affects parent order:** No (order stays NEW until ACCEPTED)

### ACCEPTED
- **Meaning:** Deal finalized; supplier assignment triggered
- **Terminal:** Yes — no further transitions
- **Affects parent order:** Yes — triggers `assign_supplier()` → order moves to WAITING_SERVICE

### EXPIRED
- **Meaning:** The 30-minute hold timed out without acceptance
- **Terminal:** Yes
- **Affects parent order:** Order remains NEW (can receive new offers or re-selections)

### WITHDRAWN
- **Meaning:** Supplier voluntarily withdrew their offer
- **Terminal:** Yes
- **Affects parent order:** No

### REJECTED
- **Meaning:** Superseded by customer selecting a different offer
- **Terminal:** Yes
- **Affects parent order:** No

### CANCELLED
- **Meaning:** Parent order was cancelled while this offer was active
- **Terminal:** Yes
- **Affects parent order:** N/A (order cancellation is the cause, not the effect)

## 5. Complete Transition Matrix

| From | Action | To | Actor | Auth Rule | Order Prereq | Offer Prereq | Locks | Side Effects | Audit Event | Idempotency | Failure |
|---|---|---|---|---|---|---|---|---|---|---|---|
| — | `submit_offer` | SUBMITTED | Supplier | `PermissionService.require(orders.offer.submit)` + actor-supplier identity | `order.status == NEW` | None (new offer) | Order row | Create OrderOffer row | `orders.offer.submitted` | Duplicate → domain error (UniqueConstraint) | OrderOfferError |
| SUBMITTED | `edit_offer` | SUBMITTED | Original submitter | Ownership: `submitted_by == actor` | `order.status == NEW` | `can_edit == True` | Order row → Offer row | Update mutable fields | `orders.offer.edited` | No changes → no-op (return unchanged offer) | OrderOfferError |
| SUBMITTED | `withdraw_offer` | WITHDRAWN | Original submitter | Ownership: `submitted_by == actor` | `order.status == NEW` | `can_withdraw == True` | Order row → Offer row | None | `orders.offer.withdrawn` | Already terminal → error | OrderOfferError |
| SUBMITTED | `select_offer` | SELECTED | Customer (order owner) | Ownership: `order.customer_profile.user == actor` | `order.status == NEW` | `can_select == True` | Order row → Target offer row → Competing offer rows | Set `selected_by`, `selected_at`, `hold_expires_at`; bulk-reject all other SUBMITTED offers | `orders.offer.selected` + `orders.offer.rejected` per competitor | Already SELECTED (same offer) → error or no-op | OrderOfferError |
| SUBMITTED | `select_offer` (competing) | REJECTED | System (side-effect) | N/A (cascading from select) | N/A | Status == SUBMITTED | Competing offer rows | None | `orders.offer.rejected` | N/A | N/A |
| SELECTED | `accept_offer` | ACCEPTED | Customer (order owner) | Ownership: `order.customer_profile.user == actor` | `order.status == NEW` | `hold_active == True` | Offer row → Order row | Call `assign_supplier()` → order to WAITING_SERVICE; Assignment created | `orders.offer.accepted` | Already ACCEPTED → error | OrderOfferError |
| SELECTED | `expire_held_offers` | EXPIRED | System (background) | None (system context) | Any (expiry is time-based) | `status == SELECTED` AND `hold_expires_at < now()` | Offer row (`skip_locked`) | None | `orders.offer.expired` | Already terminal → skip | N/A |
| SUBMITTED or SELECTED | `cancel_offers_for_order` | CANCELLED | System (side-effect of order cancellation) | None (cascading) | Order being cancelled | `is_active == True` | Per-offer rows | None | `orders.offer.cancelled` | Already terminal → skip | N/A |
| SUBMITTED | **supplier decline** | — | — | — | — | — | — | — | — | — | **INTENTIONALLY UNSUPPORTED** (hold expires naturally) |
| SELECTED | **customer deselect** | — | — | — | — | — | — | — | — | — | **UNRESOLVED** business decision (not planned for Sprint 5.2) |
| Any terminal | **resubmit** | — | — | — | — | — | — | — | — | — | **INTENTIONALLY UNSUPPORTED** (UniqueConstraint prevents re-offer) |

## 6. Authorization Matrix

| Operation | Actor Type | Enforcement Mechanism | Permission Key | Ownership Check |
|---|---|---|---|---|
| submit_offer | Supplier | `PermissionService.require()` + actor-supplier identity | `orders.offer.submit` | Actor's resolved supplier == supplier_id |
| edit_offer | Supplier | Ownership only | None | `submitted_by == actor` |
| withdraw_offer | Supplier | Ownership only | None | `submitted_by == actor` |
| select_offer | Customer | Ownership only | None | `order.customer_profile.user == actor` |
| accept_offer | Customer | Ownership only | None | `order.customer_profile.user == actor` |
| expire_held_offers | System | None | None | N/A |
| cancel_offers_for_order | System | None (cascading) | None | N/A |

## 7. Locking Matrix

| Operation | Lock 1 | Lock 2 | Lock 3 | Strategy |
|---|---|---|---|---|
| submit_offer | Order row (`select_for_update`) | — | — | Serialize concurrent submissions |
| edit_offer | Order row | Offer row | — | Consistent ordering |
| withdraw_offer | Order row | Offer row | — | Consistent ordering |
| select_offer | Order row | Target offer row | Competing offer rows (batch) | One-selected invariant |
| accept_offer | Offer row | Order row | — | Verify hold, then assign |
| expire_held_offers | Per-offer (`skip_locked`) | — | — | Allow concurrent batch calls |
| cancel_offers_for_order | Per-offer (`select_for_update`) | — | — | Within order cancellation transaction |

## 8. Database Invariant Matrix

| Constraint | Name | What It Enforces | Enforcement Level |
|---|---|---|---|
| One offer per (order, supplier) | `uq_order_offer_one_per_supplier` | No duplicate submissions | DB |
| One SELECTED offer per order | `uq_order_offer_one_selected_per_order` | At most one selected at any time | DB (conditional) |
| Tenant FK | `tenant` column | Tenant-scoped data | DB FK |
| Terminal immutability | `OFFER_TERMINAL_STATUSES` frozenset | No transitions from terminal states | **Service-layer only** |
| Order must be NEW for submission | — | Offers only on accepting orders | **Service-layer only** |
| Hold expiry determines accept eligibility | `hold_expires_at` field | Expired holds cannot be accepted | **Service-layer only** |

## 9. Side-Effect Map

| Transition | Side Effect | Target Entity | Reversible? |
|---|---|---|---|
| → SELECTED | Bulk reject competing offers | Other OrderOffer rows | **NO** (rejected offers stay rejected) |
| → SELECTED | Set hold_expires_at (30 min) | Self | Yes (expiry transitions to EXPIRED) |
| → ACCEPTED | `assign_supplier(order_id, supplier)` | Order (→ WAITING_SERVICE) | Not by offer system |
| → ACCEPTED | `AssignmentService.assign()` → creates SupplierAssignment | SupplierAssignment | Not by offer system |
| → ACCEPTED | Financial core opens | Escrow, PaymentDeadline | Not by offer system |
| → EXPIRED | None | — | — |
| → CANCELLED | None | — | — |

## 10. Order/Booking/Assignment/Financial Integration Map

| Offer Event | Order Effect | Booking Effect | Financial Effect |
|---|---|---|---|
| Offer submitted | None | None | None |
| Offer edited | None | None | None |
| Offer withdrawn | None | None | None |
| Offer selected | None (stays NEW) | None | None |
| Offer accepted | Order → WAITING_SERVICE | SupplierAssignment created | Financial core opens (escrow, deadline) |
| Offer expired | None (stays NEW) | None | None |
| Offer cancelled | None (order already cancelling) | None | None |

**Critical boundary:** Only `accept_offer` crosses into booking/assignment/financial domains. All other operations are self-contained within the OrderOffer lifecycle.

## 11. Unsupported and Unresolved Transitions

| Transition | Classification | Rationale |
|---|---|---|
| Supplier declines selection | **INTENTIONALLY UNSUPPORTED** | No model state exists for this; hold expires naturally (30 min) |
| Customer cancels/reverts selection | **UNRESOLVED BUSINESS DECISION** | Could reopen order for new offers; product team must decide |
| Resubmit after withdrawal | **INTENTIONALLY UNSUPPORTED** | `UniqueConstraint(order, supplier)` prevents it; accepted product decision |
| Admin force-expire | **PLANNED (future)** | Would need `orders.offer.admin_expire` permission key; not Sprint 5.2 |
| Admin force-accept | **UNNECESSARY** | Admin can assign directly via `AssignmentService.assign()` |

## 12. Concurrency Analysis

| Race Condition | Probability | Mitigation | Residual Risk |
|---|---|---|---|
| Two customers selecting simultaneously | Very Low (single customer per order) | `uq_order_offer_one_selected_per_order` DB constraint | None — constraint is absolute |
| Selection while supplier is withdrawing | Low | Order row locked by both; one serializes after the other | None — loser sees updated state |
| Accept race against hold expiry | Medium | `hold_active` check under lock; if expired, reject accept | None — check is atomic |
| Batch expiry concurrent with accept | Medium | `skip_locked` on expiry; accept locks the specific offer first | Expiry skips the locked offer; accept succeeds if hold valid |
| Order cancellation during selection | Low | Both lock Order row; one serializes after the other | None — either selection fails (order not NEW) or cancellation sees offer already selected |
| Two submissions by same supplier | Low | `uq_order_offer_one_per_supplier` DB constraint | None |

## 13. Cancellation Authorization Finding

### Evidence

1. `request_cancellation(*, order_id, requested_by, reason="")` — NO `PermissionService.require()` call
2. `approve_cancellation(*, order_id, changed_by=None)` — NO `PermissionService.require()` call; `changed_by` defaults to None
3. Neither function takes a `tenant_id` parameter (the order is retrieved without tenant scoping in the `select_for_update` call — but `order_id` is a UUID, making guessing impractical)
4. **Call sites outside tests:** Only `seed_product_walkthrough.py` (dev-only command, not production reachable)
5. **Portal call sites:** ZERO — no portal view currently calls either function

### Classification

**Architectural inconsistency** — not a confirmed security defect in practice today.

**Reasoning:**
- No production view/API exposes these functions to end users (zero portal call sites)
- The functions are public module-level exports available to any future consumer
- Any future view wiring them without adding its own permission check would create a security defect
- The existing order status machine does not enforce who may request or approve cancellation

### Does it block Sprint 5.2?

**No, for `select_offer` + `expire_held_offers` specifically** — because:
- `select_offer` does not call cancellation functions
- `expire_held_offers` does not call cancellation functions
- The race condition "order cancelled during selection" is handled by the Order row lock + status check, regardless of whether cancellation itself is authorized
- `cancel_offers_for_order` (the Sprint 5.3 candidate) DOES interact with cancellation and should wait

**Recommendation:** Fix cancellation authorization as a separate PR before Sprint 5.3 (which introduces `cancel_offers_for_order`). It does NOT block Sprint 5.2.

## 14. Sprint Decomposition Comparison

### Option A: select → hold expiry → accept (3 sprints)

| Sprint | Methods | Blast Radius | Testability |
|---|---|---|---|
| 5.2 | `select_offer` | Medium (rejects competing offers) | High — self-contained |
| 5.3 | `expire_held_offers` | Low (batch, skip_locked) | Very high — time-mock-based |
| 5.4 | `accept_offer` + downstream | High (crosses domains) | Medium — requires integration |

**Problem:** Splitting select from expiry means you can test selection but cannot prove the hold-timeout path until a later sprint. This leaves the SELECTED state only partially exercised.

### Option B: select + expire → accept (2 sprints) — **RECOMMENDED**

| Sprint | Methods | Blast Radius | Testability |
|---|---|---|---|
| 5.2 | `select_offer` + `expire_held_offers` | Medium (reject + time-based expiry) | High — fully self-contained |
| 5.3 | `accept_offer` + `cancel_offers_for_order` + downstream | High (crosses domains) | Medium — requires assignment/financial integration |

**Rationale:**
- Select and expire are a **natural pair** — you cannot fully test SELECTED without proving it expires
- Together they exercise the complete "hold" lifecycle without crossing domain boundaries
- The one-selected-per-order invariant is the hardest concurrency point — testing it in isolation (without accept) is cleaner
- Accept is the only operation that crosses into booking/assignment/financial — isolating it in Sprint 5.3 limits blast radius
- `cancel_offers_for_order` belongs with accept because both involve order-state interactions and cancellation authorization should be fixed first

### Option C: select + expire + cancel (without accept)

**Problem:** `cancel_offers_for_order` interacts with the cancellation authorization gap. Better to fix that gap first, then wire cancellation in Sprint 5.3 alongside accept.

## 15. Recommended Sprint 5.2 Boundary

### `select_offer()` + `expire_held_offers()`

**No prerequisite required** (cancellation remediation does NOT block these specific operations).

### What Sprint 5.2 delivers:
1. Customer can select an offer → 30-minute hold
2. All competing SUBMITTED offers are immediately REJECTED
3. Expired holds are batch-transitioned to EXPIRED by a callable method
4. The one-selected-per-order DB invariant is exercised under concurrency

### What Sprint 5.2 explicitly excludes:
- `accept_offer()` (crosses into assignment/booking/financial)
- `cancel_offers_for_order()` (interacts with cancellation authorization)
- Background scheduler (Celery task/management command invoking `expire_held_offers`)
- Views/URLs/API endpoints
- Cancellation authorization fix (separate, unblocking PR)

## 16. Acceptance Criteria

1. `select_offer(*, offer_id, actor, tenant_id)` transitions SUBMITTED → SELECTED
2. Sets `selected_by = actor`, `selected_at = now()`, `hold_expires_at = now() + 30min`
3. Bulk-rejects ALL other SUBMITTED offers for the same order (→ REJECTED terminal)
4. Only order owner (customer) can select — ownership verified
5. Order must be in NEW status
6. Concurrent selection race produces exactly one winner (TransactionTestCase + DB constraint)
7. `expire_held_offers(*, tenant_id=None)` transitions SELECTED offers where `hold_expires_at < now()` → EXPIRED
8. Uses `select_for_update(skip_locked=True)` for concurrent safety
9. Fully idempotent — re-running with no time change is a no-op
10. All mutations atomic with `AuditService.log()` call
11. No interaction with order status (order stays NEW)
12. No migration required
13. Full regression passes
14. `git diff --check` clean

## 17. Test Plan (~25–30 tests)

**select_offer:**
1. Happy path: SUBMITTED → SELECTED, fields correctly set
2. Competing offers bulk-rejected
3. Non-owner cannot select (wrong customer)
4. Order not in NEW status → rejected
5. Already-terminal offer cannot be selected
6. Another offer already SELECTED → rejected (UniqueConstraint)
7. Concurrent selection race: exactly one winner (TransactionTestCase)
8. Hold expires_at is set to 30 minutes from now (±tolerance)
9. Rejected offers are terminal (cannot be edited/withdrawn/selected after)
10. Audit event recorded with correct payload
11. Tenant isolation: cross-tenant select rejected
12. Same offer re-selected → error (already selected)

**expire_held_offers:**
13. Expired SELECTED offer transitions to EXPIRED
14. Non-expired SELECTED offer untouched
15. Already-terminal offer untouched (idempotent)
16. Multiple expired offers batch-processed in one call
17. Audit event per expired offer (actor=None)
18. tenant_id=None processes all tenants
19. tenant_id specified processes only that tenant
20. Concurrent expiry calls safe (skip_locked, no deadlock)
21. Offer that just became ACCEPTED between check and lock → skipped

## 18. Migration Determination

**No migration required.** The model already has:
- `selected_by` FK field (nullable)
- `selected_at` DateTimeField (nullable)
- `hold_expires_at` DateTimeField (nullable)
- `UniqueConstraint(fields=["order"], condition=Q(status="selected"), name="uq_order_offer_one_selected_per_order")`

All created in migration `0008_orderoffer.py`.

## 19. Critical Architecture Questions — Answered

| # | Question | Answer | Evidence |
|---|---|---|---|
| 1 | Is SELECTED the hold state? | **YES** — SELECTED IS the hold state. No separate HELD status needed. | `OrderOfferStatus.SELECTED` comment: "30-minute hold active"; `hold_expires_at` field on same model |
| 2 | Does select immediately reject competing offers? | **YES** — per architecture assessment §5.1 | Assessment: "All other SUBMITTED --> REJECTED" |
| 3 | Is competing-offer rejection irreversible? | **YES** | REJECTED is in `OFFER_TERMINAL_STATUSES`; no undo transition exists |
| 4 | Can customer change selection before acceptance? | **UNRESOLVED** business decision | Not supported; no transition from SELECTED back to open |
| 5 | Can supplier decline a selection? | **INTENTIONALLY UNSUPPORTED** | No model state; hold expires naturally |
| 6 | What happens when hold expires? | SELECTED → EXPIRED; order stays NEW | Architecture assessment §5.2 |
| 7 | Does expiration restore rejected offers? | **NO** | Rejected offers stay REJECTED (terminal); order returns to NEW for new submissions |
| 8 | Can a withdrawn/rejected offer be resubmitted? | **NO** | `UniqueConstraint(order, supplier)` prevents it |
| 9 | When is assignment created? | At `accept_offer()` time, not at `select_offer()` | Assessment: "Supplier assigned? **No** — hold only" |
| 10 | When does order status change? | At `accept_offer()` → WAITING_SERVICE | Assessment: "Order status after accept? Transitions to WAITING_SERVICE" |
| 11 | When do financial workflows begin? | At assignment via `AssignmentService._open_financial_core_for_assignment()` | `assignment_service.py` line at end of `assign()` |
| 12 | Sole writer for each transition? | `OrderOfferService` — enforced by architecture guardrails | `ServiceSupplierSoleWriterTest` pattern |
| 13 | select_for_update on what? | Order (first) → target offer → competing offers (batch) | Consistent with existing edit/withdraw pattern |
| 14 | DB constraints enforcing invariants? | Two: one-per-supplier, one-selected-per-order | Migration 0008 |
| 15 | Service-only invariants? | Terminal immutability, order-NEW prerequisite, hold-active for accept | In service code, not DB |
| 16 | Remaining race conditions? | Accept vs expire (handled by lock + hold_active check) | §12 analysis above |
| 17 | Scheduler needed for expiration? | Not for Sprint 5.2 — method is callable; scheduler is infra (later) | Assessment §5.2: "scheduling infrastructure, not domain logic" |
| 18 | Model supports lifecycle without migration? | **YES** — all fields and constraints exist | Migration 0008 verified |

## 20. GO / NO-GO

### **GO**

| Condition | Status |
|---|---|
| Model ready (all fields, constraints) | ✅ |
| No migration needed | ✅ |
| Service patterns established (Sprint 5.1) | ✅ |
| Concurrency strategy proven (UniqueConstraint) | ✅ |
| Authorization model clear (ownership for select, system for expire) | ✅ |
| No cross-domain interaction | ✅ |
| Cancellation gap does NOT block select/expire | ✅ |
| Test plan defined | ✅ |
| Acceptance criteria explicit | ✅ |
| Blast radius bounded | ✅ |

**Sprint 5.2 scope: `select_offer()` + `expire_held_offers()` — approved for implementation.**

---

**Assessment complete. Do not implement until this assessment is explicitly approved.**
