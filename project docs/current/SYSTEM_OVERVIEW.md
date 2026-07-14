# EXECUTIVE SYSTEM OVERVIEW

**Last verified HEAD:** eb51018ffbc9faeebae08adebcc21d6dbfe7b92e (merge of PR #1)
**Last verified date:** 2026-07-14 (post-merge sync)

---

## What Is This System?

**taasisatSenior** (also called "Salmandyar" / "Elder Companion") is a Django multi-tenant enterprise platform for a senior-care service marketplace. Customers request in-home care services; independent providers and organizations deliver them.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12, Django 5.2.16 |
| Database | PostgreSQL 16 |
| Frontend | Django Templates + HTMX/Alpine.js + Tailwind CSS |
| Cache | Redis (fallback LocMemCache) |
| Task Queue | Celery (synchronous in tests) |
| UI Language | Persian (Farsi) — RTL-first |
| Date System | Jalali/Shamsi |
| Fonts | IRANSans/Vazirmatn |

## Architecture

- **25 Django apps** in `src/apps/` + 1 config package
- **~70 concrete models** across 16 apps with models
- **Server-rendered** — no SPA, HTMX progressive enhancement
- **Event-driven** — ~270+ CES event types, outbox pattern
- **Multi-tenant** — TenantAwareModel base, tenant_id on all business models
- **Service-layer architecture** — business logic in services, not views

## Current Maturity

| Dimension | Status |
|-----------|--------|
| Foundation (kernel, auth, RBAC) | Complete |
| Customer Experience | Phase 1-2 complete |
| Provider Experience | Phase 1 complete |
| Organization Experience | Phase 1 complete |
| Financial Core | PR-A (commission/deadlines) + PR-B (escrow/disputes) complete |
| Offer Marketplace | Phase 1 (domain model) complete, committed in ce3b30e |
| Real PSP Integration | Not started (fake provider only) |
| Real SMS/Notification | Not started (fake providers only) |
| Production Deployment | Not started |

## What Works End-to-End

1. Authentication via phone + OTP (fake SMS)
2. Customer/Provider/Organization registration and profiles
3. Service catalog and order creation
4. Matching engine (eligibility + ranking)
5. Operator assignment with concurrency protection
6. Execution sessions (start/complete/close)
7. Financial document generation
8. Wallet operations (credit/debit/refund)
9. Dispute flow with escrow block/release
10. Reviews and reputation

## What Does NOT Work End-to-End

1. Real payment processing (fake PSP adapter only)
2. Real notifications (fake SMS/email/push providers)
3. Offer Marketplace service layer (Phase 1 model only, no services)
4. Deadline expiry (safety gate disabled by default)
5. Pre-service payment (gated, disabled by default)
6. Geospatial features (GIS disabled on Windows)
7. CI/CD pipeline (never executed)

## Key Architectural Constraints

1. **Repository is source of truth** — no Blueprint, no memory overrides
2. **Governance rules** — 10 mandatory rules for every task
3. **Incremental implementation** — small phases, stop for review
4. **No scope expansion** — complete only approved tasks
5. **Traceability** — every change documented in `project docs/traceability/`
