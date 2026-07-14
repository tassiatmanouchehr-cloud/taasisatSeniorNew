# RECOMMENDED REVIEW ORDER

---

## For Architecture Review

1. `canonical docs/06_PERMISSION_AND_TENANT_MODEL.md` — tenant isolation and RBAC (CRITICAL findings)
2. `canonical docs/12_DEFECT_AND_RISK_REGISTER.md` — all findings
3. `canonical docs/07_FINANCIAL_SYSTEM_AS_IS.md` — money flows and escrow
4. `canonical docs/05_RUNTIME_WORKFLOWS.md` — how business processes execute
5. `canonical docs/04_DATA_OWNERSHIP_AND_RELATIONSHIPS.md` — model relationships
6. `canonical docs/15_ACTIVE_ARCHITECTURE_DECISIONS.md` — binding decisions

## For Security Review

1. `mimo change/audit/05_SECURITY_AND_TENANCY_FINDINGS.md` — all security findings
2. `canonical docs/06_PERMISSION_AND_TENANT_MODEL.md` — permission model
3. `mimo change/audit/01_CRITICAL_FINDINGS.md` — CRITICAL findings
4. `mimo change/audit/06_FINANCIAL_INTEGRITY_FINDINGS.md` — financial security

## For Code Review (Phase 1 Commit)

1. `src/apps/orders/models.py` — OrderOffer model
2. `src/apps/orders/admin.py` — OrderOfferAdmin
3. `src/apps/orders/migrations/0008_orderoffer.py` — migration
4. `src/apps/orders/tests/test_order_offer_model.py` — tests
5. `canonical docs/17_PROJECT_CONTINUATION.md` — current state

## For Implementation (Phase 2)

1. `canonical docs/18_NEXT_TASK.md` — next task
2. `canonical docs/05_RUNTIME_WORKFLOWS.md` — workflow context
3. `canonical docs/04_DATA_OWNERSHIP_AND_RELATIONSHIPS.md` — relationships
4. `canonical docs/10_TEST_CONFIDENCE_MATRIX.md` — test expectations
5. `canonical docs/12_DEFECT_AND_RISK_REGISTER.md` — known risks
