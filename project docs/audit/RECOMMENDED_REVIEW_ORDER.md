# RECOMMENDED REVIEW ORDER

**Updated:** 2026-07-14 — paths synchronized to the active `project docs/`
structure (the former `canonical docs/` and `mimo change/` paths are archived).

---

## For Architecture Review

1. `project docs/current/PERMISSIONS_AND_TENANCY.md` — tenant isolation and RBAC (CRITICAL findings)
2. `project docs/quality/DEFECT_AND_RISK_REGISTER.md` — all findings
3. `project docs/current/FINANCIAL_SYSTEM.md` — money flows and escrow
4. `project docs/current/RUNTIME_WORKFLOWS.md` — how business processes execute
5. `project docs/current/DATA_RELATIONSHIPS.md` — model relationships
6. `project docs/current/ACTIVE_ARCHITECTURE_DECISIONS.md` — binding decisions

## For Security Review

1. `project docs/audit/SECURITY_AND_TENANCY.md` — all security findings
2. `project docs/current/PERMISSIONS_AND_TENANCY.md` — permission model
3. `project docs/audit/CRITICAL_FINDINGS.md` — CRITICAL findings
4. `project docs/audit/FINANCIAL_INTEGRITY.md` — financial security

## For Code Review (Offer Marketplace Phase 1 — committed in ce3b30e)

1. `src/apps/orders/models.py` — OrderOffer model
2. `src/apps/orders/admin.py` — OrderOfferAdmin
3. `src/apps/orders/migrations/0008_orderoffer.py` — migration
4. `src/apps/orders/tests/test_order_offer_model.py` — tests
5. `project docs/02_PROJECT_CONTINUATION.md` — current state

## For Implementation (next phase)

1. `project docs/03_NEXT_TASK.md` — next task
2. `project docs/IMPLEMENTATION_ROADMAP.md` — active implementation order
3. `project docs/current/RUNTIME_WORKFLOWS.md` — workflow context
4. `project docs/current/DATA_RELATIONSHIPS.md` — relationships
5. `project docs/quality/TEST_CONFIDENCE_MATRIX.md` — test expectations
6. `project docs/quality/DEFECT_AND_RISK_REGISTER.md` — known risks
