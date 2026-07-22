# ORDER OFFER SPRINT 5.2 SCOPE ASSESSMENT

**Date:** 2026-07-22
**Repository HEAD:** `8910a7c` (main, post-PR #43 canonical documentation merge)
**Assessor:** Kiro
**Status:** Immutable assessment — do not edit after approval

---

## 1. Current Repository Baseline

| Metric | Value |
|---|---|
| Main HEAD | `8910a7c` |
| Last merged feature PR | #41 (Sprint 5.1 — OrderOffer submission lifecycle) |
| Full regression | 2,546/2,546 PASS (CI evidence) |
| OrderOffer service tests | 29 |
| OrderOffer model tests | 40 |
| Architecture guardrail tests | 28 |

## 2. Existing Sprint 5.1 Behavior (Verified from Source)

Sprint 5.1 implemented **three** service methods, not one:

| Method | Status | Tests |
|---|---|---|
| `OrderOfferService.submit_offer()` | IMPLEMENTED | 13 tests |
| `OrderOfferService.edit_offer()` | IMPLEMENTED | 8 tests |
| `OrderOfferService.withdraw_offer()` | IMPLEMENTED | 8 tests |

**This means the proposed "Sprint 5.2: edit + withdraw" decomposition is INVALID — both operations already exist.**

### Established Patterns

| Pattern | Implementation |
|---|---|
| Lock ordering | Order row first, then offer row |
| Authorization (submit) | `PermissionService.require(orders.offer.submit)` |
| Authorization (edit/withdraw) | Ownership: `offer.submitted_by == actor` |
| Tenant isolation | All queries scoped by `tenant_id` |
| Audit logging | `AuditService.log()` on every mutation |
| Error model | `OrderOfferError` domain exception |
| Idempotency | Terminal-status check prevents double transitions |
| Sole writer | Only `OrderOfferService` writes to `OrderOffer` |

## 3. State-Transition Matrix (Complete Lifecycle)

```
                    SUBMITTED ──── [edit_offer] ────→ SUBMITTED (fields updated)
                       │
         ┌─────────────┼──────────────┐
         │             │              │
    [withdraw]    [select]    [cancel_offers_for_order]
         │             │              │
         ▼             ▼              ▼
     WITHDRAWN      SELECTED       CANCELLED
     (terminal)       │            (terminal)
                      │
         ┌────────────┼────────────┐
         │            │            │
    [expire]    [accept]    [cancel during hold]
         │            │            │
         ▼            ▼            ▼
      EXPIRED      ACCEPTED     CANCELLED
     (terminal)   (terminal)   (terminal)
```

**Implemented transitions (Sprint 5.1):**
- → SUBMITTED (submit_offer)
- SUBMITTED → SUBMITTED (edit_offer, fields only)
- SUBMITTED → WITHDRAWN (withdraw_offer)

**Remaining transitions (Sprint 5.2+ candidates):**
- SUBMITTED → SELECTED (select_offer)
- SUBMITTED → REJECTED (bulk rejection by select_offer on competing offers)
- SUBMITTED → CANCELLED (cancel_offers_for_order)
- SELECTED → ACCEPTED (accept_offer)
- SELECTED → EXPIRED (expire_held_offers)
- SELECTED → CANCELLED (cancel during hold)

## 4. Per-Operation Analysis

### 4.1 select_offer()

| Dimension | Finding |
|---|---|
| **Actor** | Customer (order owner) |
| **Permission key** | None required — order ownership is the boundary |
| **Source states** | Offer: SUBMITTED; Order: NEW |
| **Target state** | Offer: SELECTED |
| **Order status after** | Remains NEW (no assignment yet) |
| **Supplier prerequisites** | None (the offer already validated supplier at submission) |
| **Ownership rule** | `order.customer_profile.user == actor` |
| **Tenant isolation** | `offer.tenant_id == order.tenant_id` (invariant from submission) |
| **Row locks** | Order row first (verify state + one-selected invariant), then target offer row |
| **Idempotency** | Re-selecting an already-SELECTED offer (same offer) → no-op or error |
| **Audit event** | `orders.offer.selected` (actor, offer_id, order_id) |
| **Domain events** | Reject all other SUBMITTED offers → `orders.offer.rejected` per offer |
| **Concurrency risks** | HIGH — two concurrent selections must result in exactly one SELECTED (DB UniqueConstraint `uq_order_offer_one_selected_per_order` is the backstop) |
| **Interaction with other offers** | **Destructive** — rejects ALL other SUBMITTED offers for this order |
| **Interaction with assignment** | None — selection does NOT assign the supplier |
| **Interaction with booking** | None |
| **Interaction with financial** | None (hold only; no payment triggered) |
| **Model changes** | None — `selected_by`, `selected_at`, `hold_expires_at` fields already exist |
| **Migration changes** | None |
| **Required tests** | Happy path, concurrent selection race, non-owner rejection, wrong order status, already-selected, competing-offer rejection, hold-expiry timestamp set, UniqueConstraint enforcement |
| **Reusable services** | None needed (self-contained within OrderOfferService) |
| **Risks** | Competing-offer rejection is irreversible; unresolved: can customer cancel a selection? |

### 4.2 accept_offer()

| Dimension | Finding |
|---|---|
| **Actor** | Customer (order owner) |
| **Permission key** | None required — order ownership is the boundary |
| **Source states** | Offer: SELECTED (with active hold) |
| **Target state** | Offer: ACCEPTED |
| **Order status after** | Transitions to WAITING_SERVICE via `status_machine.assign_supplier()` |
| **Supplier prerequisites** | Supplier must still be ACTIVE at acceptance time (re-verify) |
| **Ownership rule** | `order.customer_profile.user == actor` (same as select) |
| **Tenant isolation** | Inherited from offer/order |
| **Row locks** | Offer row first (verify hold_active), then Order row (for assign_supplier) |
| **Idempotency** | Re-accepting an already-ACCEPTED offer → no-op or error |
| **Audit event** | `orders.offer.accepted` (actor, offer_id, order_id, supplier_id) |
| **Domain events** | Order assignment event (from status_machine) |
| **Concurrency risks** | Medium — hold protects against competing selections; verify hold not expired at acceptance time |
| **Interaction with other offers** | None (competing offers already REJECTED at select time) |
| **Interaction with assignment** | **Direct** — calls `status_machine.assign_supplier()` or `AssignmentService.assign()` |
| **Interaction with booking** | `AssignmentService.assign()` creates `SupplierAssignment` and may trigger financial core |
| **Interaction with financial** | Through `AssignmentService.assign()` → financial core integration (escrow, payment deadline) |
| **Model changes** | None — all fields exist |
| **Migration changes** | None |
| **Required tests** | Happy path, expired hold rejected, wrong offer status, non-owner, order already assigned, concurrent accept race, supplier deactivated between select and accept |
| **Reusable services** | `status_machine.assign_supplier()` or `AssignmentService.assign()` |
| **Risks** | **HIGH** — crosses domain boundary into booking/financial. This is the riskiest operation. Cancellation authorization gap must be fixed first. |

### 4.3 expire_held_offers()

| Dimension | Finding |
|---|---|
| **Actor** | System (background job, no human actor) |
| **Permission key** | None — system context |
| **Source states** | Offer: SELECTED where `hold_expires_at < now()` |
| **Target state** | Offer: EXPIRED |
| **Order status after** | Remains NEW (order returns to offer-accepting state) |
| **Ownership rule** | N/A (system operation) |
| **Row locks** | `select_for_update(skip_locked=True)` per offer (allows concurrent calls) |
| **Idempotency** | Fully idempotent — only affects offers where hold has actually expired |
| **Audit event** | `orders.offer.expired` (actor=None, system context) |
| **Concurrency risks** | Low — `skip_locked` prevents deadlocks; concurrent expiry calls are safe |
| **Interaction with other offers** | None |
| **Interaction with assignment** | None (order stays NEW, no assignment triggered) |
| **Interaction with financial** | None |
| **Model changes** | None |
| **Migration changes** | None |
| **Required tests** | Expired offer transitions, non-expired offer untouched, idempotency, batch processing, skip_locked behavior |
| **Reusable services** | None |
| **Risks** | Low — self-contained, no side effects on other entities |

### 4.4 cancel_offers_for_order()

| Dimension | Finding |
|---|---|
| **Actor** | System (side-effect of order cancellation) |
| **Permission key** | None — cascading from order cancellation (which itself lacks permission checks — the open gap) |
| **Source states** | Any non-terminal offer status (SUBMITTED or SELECTED) |
| **Target state** | Offer: CANCELLED |
| **Order status after** | Already being cancelled (this is a side-effect) |
| **Row locks** | Per-offer `select_for_update()` |
| **Idempotency** | Fully idempotent — only affects non-terminal offers |
| **Audit event** | `orders.offer.cancelled` (actor=cancellation initiator or None) |
| **Concurrency risks** | Must handle race with concurrent selection (offer being selected while cancellation runs) |
| **Interaction with other offers** | Cancels ALL non-terminal offers for the order |
| **Interaction with assignment** | None (order is being cancelled) |
| **Interaction with financial** | Through order cancellation's own financial implications (separate concern) |
| **Model changes** | None |
| **Migration changes** | None |
| **Required tests** | Cancels SUBMITTED offers, cancels SELECTED offers, skips terminal offers, idempotency |
| **Risks** | Medium — depends on cancellation authorization remediation being done first |

## 5. Prerequisite: Cancellation Authorization Remediation

The architecture assessment (2026-07-21) explicitly states:

> **MUST be remediated before Sprint 5.2** (selection/acceptance), because:
> - `select_offer()` rejects competing offers (a destructive action)
> - `accept_offer()` triggers `assign_supplier()` → order state change
> - Cancellation during a hold interacts with the selected offer

**Current state verified:** `status_machine.request_cancellation()` and `approve_cancellation()` have ZERO `PermissionService.require()` calls. Any authenticated user with an `order_id` can cancel any order.

**This is a blocking prerequisite for select/accept/cancel_offers operations.**

## 6. Candidate Scope Comparison

### Proposed: "Sprint 5.2: edit + withdraw" — **REJECTED**

**Reason:** Both `edit_offer()` and `withdraw_offer()` are **already implemented and tested** in Sprint 5.1. This decomposition is based on outdated information.

### Alternative A: Sprint 5.2 = select + expire (RECOMMENDED)

| Pro | Con |
|---|---|
| Self-contained — no cross-domain interaction | Does not complete the lifecycle (accept deferred) |
| No financial integration | Competing-offer rejection is irreversible |
| No assignment/booking dependency | Requires cancellation remediation first |
| Expire is the simplest remaining operation | — |
| Tests the one-selected-per-order concurrency invariant | — |
| Model is already fully prepared (all fields exist) | — |

### Alternative B: Sprint 5.2 = select + expire + accept

| Pro | Con |
|---|---|
| Completes the full lifecycle in one sprint | accept crosses into booking/assignment domain |
| Proves end-to-end from submit to assignment | Larger blast radius |
| — | Requires deciding how to invoke assignment (direct or via AssignmentService) |
| — | Financial core integration triggered |
| — | More complex concurrency (expired hold vs accept race) |

### Alternative C: Sprint 5.2 = select + expire + cancel_offers

| Pro | Con |
|---|---|
| Covers all selection-related transitions | cancel_offers depends on cancellation authorization fix |
| No assignment/booking integration | Three operations in one sprint (larger review) |
| — | cancel_offers is technically a side-effect, not a standalone action |

## 7. Recommended Sprint 5.2 Scope

### **GO: select_offer + expire_held_offers**

**With mandatory prerequisite: cancellation authorization remediation as a separate, preceding PR.**

### Rationale

1. `select_offer` is the critical next lifecycle step — it enables the marketplace to function
2. `expire_held_offers` is its natural companion (what happens when the hold times out)
3. Together they test the most complex concurrency invariant (one-selected-per-order)
4. Neither requires crossing into booking, assignment, or financial domains
5. Both use only existing model fields — zero migrations needed
6. The cancellation remediation is a separate, focused fix that unblocks this work

### Explicit Exclusions

| Operation | Reason for Exclusion | Target Sprint |
|---|---|---|
| `accept_offer()` | Crosses into booking/assignment/financial domains; requires separate design for the integration boundary | Sprint 5.3 |
| `cancel_offers_for_order()` | Side-effect of cancellation; should be wired after cancellation authorization is fixed and select/expire are proven | Sprint 5.3 |
| Views/URLs/API for offers | Service layer must be complete before exposing UI/API | Sprint 5.4+ |
| Background scheduler (Celery task for expiry) | Scheduling infrastructure, not domain logic | Sprint 5.3+ |
| `edit_offer()` | Already implemented (Sprint 5.1) | N/A |
| `withdraw_offer()` | Already implemented (Sprint 5.1) | N/A |

## 8. Acceptance Criteria

### Sprint 5.2: select_offer + expire_held_offers

1. `OrderOfferService.select_offer(*, offer_id, actor, tenant_id)` transitions a SUBMITTED offer to SELECTED
2. Selection sets `selected_by`, `selected_at`, and `hold_expires_at` (30-minute hold)
3. Selection bulk-rejects all other SUBMITTED offers for the same order
4. Only the order owner (customer) can select
5. Only one offer per order can be SELECTED at a time (DB UniqueConstraint enforced)
6. Selection fails if the order is not in NEW status
7. Concurrent selection races produce exactly one SELECTED offer (proven by a TransactionTestCase)
8. `OrderOfferService.expire_held_offers(*, tenant_id=None)` transitions all SELECTED offers with `hold_expires_at < now()` to EXPIRED
9. Expiry is idempotent — calling twice with no time change is a no-op
10. Expiry uses `select_for_update(skip_locked=True)` for safe concurrent invocation
11. All mutations are atomic with audit logging
12. Full regression passes
13. `manage.py check` clean
14. `git diff --check` clean

### Prerequisite (separate PR, must merge first)

15. `request_cancellation()` and `approve_cancellation()` enforce permission via `PermissionService.require()` with new `orders.cancellation.request` / `orders.cancellation.approve` keys

## 9. Test Plan

### New Tests Required (~25-35)

**select_offer:**
- Happy path: SUBMITTED → SELECTED, fields set, competing offers REJECTED
- Non-owner cannot select
- Wrong order status (not NEW) prevents selection
- Already-terminal offer cannot be selected
- Already-selected offer on same order prevents new selection (UniqueConstraint)
- Concurrent selection race: exactly one winner (TransactionTestCase)
- Hold expires_at is set to 30 minutes from now
- Rejected offers become terminal (cannot be edited/withdrawn/selected after)
- Audit event recorded

**expire_held_offers:**
- Expired offer transitions to EXPIRED
- Non-expired offer untouched
- Already-terminal offer untouched
- Batch processes all eligible offers
- Idempotent (double call, same result)
- Uses skip_locked (no deadlock with concurrent calls)
- Audit event recorded with actor=None

**Cancellation remediation (prerequisite, separate test file):**
- Unauthorized user cannot request cancellation
- Unauthorized user cannot approve cancellation
- Authorized user with correct key can request/approve
- Permission denial produces PermissionDenied error

## 10. Documentation Update Plan

After Sprint 5.2 implementation:

1. Update `04_IMPLEMENTATION_STATUS.md` — add select/expire to implemented, update test count
2. Append to `traceability/IMPLEMENTATION_JOURNAL.md` — Sprint 5.2 entry
3. Update `03_DOMAIN_WORKFLOWS.md` §6 — mark select/expire as IMPLEMENTED

## 11. Required Model or Migration Changes

**None.** All required fields already exist on the `OrderOffer` model:
- `selected_by` (FK, nullable)
- `selected_at` (DateTimeField, nullable)
- `hold_expires_at` (DateTimeField, nullable)
- `UniqueConstraint` on `(order)` where `status='selected'` already exists

## 12. Required Permission Changes

**For the prerequisite (cancellation remediation):**
- Register `orders.cancellation.request` in `apps/kernel/permissions/keys.py`
- Register `orders.cancellation.approve` in `apps/kernel/permissions/keys.py`
- Add `PermissionService.require()` calls in `status_machine.request_cancellation()` and `approve_cancellation()`

**For Sprint 5.2 (select/expire):**
- None — selection is customer-ownership-authorized, not RBAC-gated
- Expiry is system-context, no permission check needed

## 13. Risks and Unresolved Questions

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | Cancellation remediation may break existing callers | Medium | Check all production call sites of `request_cancellation`/`approve_cancellation` before adding permission checks |
| 2 | Competing-offer rejection is irreversible | Low | Accepted product decision per architecture assessment |
| 3 | Hold duration (30 min) — should it be tenant-configurable? | Low | Defer to later; hardcode in Sprint 5.2, make configurable in Sprint 5.3+ |
| 4 | Can customer cancel a selection? | Unresolved business decision | Defer — not required for Sprint 5.2 minimum scope |
| 5 | Can supplier decline a selection? | Unresolved business decision | Defer — hold expires naturally if not accepted |

## 14. GO / NO-GO Recommendation

### **GO — with sequenced prerequisite**

| Condition | Status |
|---|---|
| Model ready | ✅ All fields and constraints exist |
| Service patterns established | ✅ Sprint 5.1 provides the template |
| No migration needed | ✅ |
| Concurrency strategy defined | ✅ (architecture assessment §7) |
| Authorization model clear | ✅ (ownership for select, system for expire) |
| Test plan defined | ✅ |
| Prerequisite identified | ✅ (cancellation remediation) |
| Financial integration deferred | ✅ (accept is Sprint 5.3) |
| Risks enumerated | ✅ |

**Execution order:**
1. PR: Fix cancellation authorization (separate, focused, ~50 lines + tests)
2. PR: Sprint 5.2 — select_offer + expire_held_offers (~200 lines service + ~350 lines tests)

---

**Assessment complete. Do not implement Sprint 5.2 until this assessment is approved.**
