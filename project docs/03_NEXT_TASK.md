# NEXT TASK

---

## COMPLETED (previously listed here)

### Commit Phase 1 OrderOffer Implementation — DONE

OrderOffer Phase 1 (model, migration `orders/0008_orderoffer.py`, admin,
40 tests) was committed in `ce3b30e`. This item is closed
(see `quality/COMPLETION_BACKLOG.md` BG-001).

---

## IMMEDIATE NEXT TASK

### Phase 1 — Registration and Verification Workflows

Defined in **`IMPLEMENTATION_ROADMAP.md`** (the single active implementation
order). Awaiting owner approval to start.

Scope summary:

1. P0 hygiene first: fix or formally accept the pre-existing seed test race
   condition (BG-002) so full regression is deterministic
2. Complete customer / caregiver / company registration workflows
3. Platform-admin manual verification workflow for `VerificationDocument`
   (review queue, approve/reject, profile `verification_status` roll-up)
4. Profile completion recomputation
5. Verification strategy interface with manual implementation only
   (future AI verification remains a documented placeholder)

Note: the previously listed follow-up "Phase 2: OrderOfferService" is now
scheduled as roadmap Phase 5 (Marketplace Order Workflow) and must not be
started before roadmap Phases 1–4.
