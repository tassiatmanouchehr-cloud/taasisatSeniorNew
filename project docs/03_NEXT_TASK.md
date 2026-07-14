# NEXT TASK

---

## COMPLETED (previously listed here)

### Commit Phase 1 OrderOffer Implementation — DONE

OrderOffer Phase 1 (model, migration `orders/0008_orderoffer.py`, admin,
40 tests) was committed in `ce3b30e`. This item is closed
(see `quality/COMPLETION_BACKLOG.md` BG-001).

### Fix BG-002 Seed order_number Collision — DONE (2026-07-14)

Bounded savepoint-wrapped retry in `Order.save()` + 6-digit suffix.
No migration. 8 new regression tests. This was the P0 hygiene precursor
to roadmap Phase 1 (see BG-002 in `quality/COMPLETION_BACKLOG.md`, CL-017).

---

## IMMEDIATE NEXT TASK

### Phase 1 — Registration and Verification Workflows

Defined in **`IMPLEMENTATION_ROADMAP.md`** (the single active implementation
order). Awaiting owner approval to start.

Scope summary:

1. ~~P0 hygiene: BG-002~~ — DONE (see above)
2. Complete customer / caregiver / company registration workflows
3. Platform-admin manual verification workflow for `VerificationDocument`
   (review queue, approve/reject, profile `verification_status` roll-up)
4. Profile completion recomputation
5. Verification strategy interface with manual implementation only
   (future AI verification remains a documented placeholder)

Note: the previously listed follow-up "Phase 2: OrderOfferService" is now
scheduled as roadmap Phase 5 (Marketplace Order Workflow) and must not be
started before roadmap Phases 1–4.
