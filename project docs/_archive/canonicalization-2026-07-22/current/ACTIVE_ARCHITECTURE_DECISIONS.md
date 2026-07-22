# ACTIVE ARCHITECTURE DECISIONS

**Last verified HEAD:** a5dbaf28703142edaa1d770ea8f3c2a45a12640f
**Last verified date:** 2026-07-14

---

## Binding Decisions (DO NOT REVISIT)

| # | Decision | Rationale | Affected Modules |
|---|----------|-----------|-----------------|
| 1 | **One OrderOffer per (order, supplier)** — unconditional uniqueness | Stable identity, clean audit, reliable reporting | orders |
| 2 | **PaymentDeadline reuse** — single canonical deadline engine | No separate offer-hold scheduler | commission, orders |
| 3 | **Assignment after successful payment** — SupplierAssignment created only when payment succeeds | Prevents 9 premature side effects | orders, booking |
| 4 | **Repository is source of truth** — no Blueprint, no memory overrides | Always verify from code | all |
| 5 | **Governance rules** — all 10 rules mandatory | Traceability, safety | all |
| 6 | **Incremental implementation** — small phases, stop for review | Risk management | all |
| 7 | **Traceability** — every change documented in `project docs/traceability/` | History preservation | all |
| 8 | **No premature payment coupling** — Phase 1 model has no PaymentIntent references | Clean separation | orders |

## Active ADMs (Offer Marketplace)

| ADM | Decision | Status |
|-----|----------|--------|
| ADM-001 | OrderOffer.SELECTED is the hold | VERIFIED |
| ADM-002 | Assignment after payment (Option B) | VERIFIED |
| ADM-003 | Marketplace visibility guard | RESOLVED_IN_CONTRACT |
| ADM-004 | One active hold per order | RESOLVED_IN_CONTRACT |
| ADM-005 | Payment failure doesn't expire hold | RESOLVED_IN_CONTRACT |
| ADM-006 | Ownership enforced in services | RESOLVED_IN_CONTRACT |
| ADM-007 | PostgreSQL for all tests | VERIFIED |
| ADM-008 | Existing operator-assignment flow preserved | VERIFIED |
| ADM-009 | Real integrations out of scope | KNOWN_LIMITATION |
| ADM-010 | Money representation DecimalField(14,2) | VERIFIED |
| ADM-011 | PaymentDeadline reuse for hold | VERIFIED |
| ADM-012 | PaymentIntent.order_offer FK (1:N) | RESOLVED_IN_CONTRACT |
| ADM-013 | One canonical OrderOffer per (order, supplier) | VERIFIED_IN_IMPLEMENTATION |

## Architecture-Level ADRs (originals archived under `_archive/documentation/20260714-124624/docs/adr/`; decisions remain ACTIVE)

| ADR | Decision | Status |
|-----|----------|--------|
| ADR-001 | Enterprise Architecture Freeze | ACTIVE |
| ADR-002 | Matching Engine Foundation | ACTIVE |
| ADR-003 | API Foundation on DRF | ACTIVE |
| ADR-004 | apps.wallet as Canonical Wallet | ACTIVE |
| ADR-005 | PaymentIntent vs PaymentTransaction | ACTIVE |
| ADR-006 | Reporting as Pure Read Layer | ACTIVE |
| ADR-007 | Service Layer Ownership | ACTIVE |
| ADR-008 | Demand-Side Domain Model | ACTIVE |
| ADR-009 | Organization RBAC & Eligibility | ACTIVE |
| ADR-010 | Canonical Permission-Key Registry | ACTIVE |
| ADR-011 | Commission Policy Engine Foundation | ACTIVE |
| ADR-012 | Financial Core PR-B: Escrow, Disputes | ACTIVE |
