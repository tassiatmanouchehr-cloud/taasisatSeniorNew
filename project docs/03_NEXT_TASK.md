# NEXT TASK

---

## COMPLETED (previously listed here)

### Commit Phase 1 OrderOffer Implementation — DONE

OrderOffer Phase 1 (model, migration `orders/0008_orderoffer.py`, admin,
40 tests) was committed in `ce3b30e`. This item is closed
(see `quality/COMPLETION_BACKLOG.md` BG-001).

### Fix BG-002 Seed order_number Collision — DONE and MERGED (2026-07-14)

Bounded savepoint-wrapped retry in `Order.save()` + 6-digit suffix.
No migration. 8 new regression tests. Merged to main via PR #1
(merge commit `eb51018`) with full regression 1680/1680 green.
This was the P0 hygiene precursor to roadmap Phase 1
(see BG-002 in `quality/COMPLETION_BACKLOG.md`, CL-017).

### Phase 1.1 — Manual Document Verification (Caregiver + Organization) — IMPLEMENTED, PR PENDING (2026-07-15)

`VerificationReviewService` (approve/reject/request_correction), the
`accounts.document.review` permission, admin_portal review queue/detail/
file/review-action views and templates, and owner-facing reason display.
41 new tests (25 service-layer + 16 view-layer), full regression
1721/1721 green. Branch `phase1-registration-manual-verification`, PR
created but **not yet merged** — see `traceability/IMPLEMENTATION_JOURNAL.md`
and `traceability/ARCHITECTURE_DECISION_LOG.md` (ADM-014) for the full
record, including two explicit scope decisions (customer verification
deferred — no domain-model support exists; profile roll-up deferred — no
required-document policy exists).

---

## IMMEDIATE NEXT TASK

### Merge the Phase 1.1 PR, then continue Phase 1 — Registration and Verification Workflows

Defined in **`IMPLEMENTATION_ROADMAP.md`** (the single active implementation
order).

Remaining Phase 1 scope after Phase 1.1 merges:

1. ~~P0 hygiene: BG-002~~ — DONE
2. ~~Customer / caregiver / company registration workflows~~ — VERIFIED, no defect found (Phase 1.1 Part A)
3. ~~Platform-admin manual verification workflow~~ — IMPLEMENTED for caregiver/organization (Phase 1.1); profile `verification_status` roll-up remains — **no required-document-type policy exists yet; do not guess one, define it explicitly first**
4. Profile completion recomputation — not started
5. ~~Verification strategy interface~~ — `DocumentVerificationEvaluator` Protocol added, no implementation (by design)
6. New, not yet scoped: customer document verification (no domain-model support currently exists — requires its own decision before implementation)

Note: the previously listed follow-up "Phase 2: OrderOfferService" is now
scheduled as roadmap Phase 5 (Marketplace Order Workflow) and must not be
started before roadmap Phases 1–4.
