# IMPLEMENTATION STATUS

**Last Verified:** 2026-07-22
**Branch:** `feature/order-offer-selection-expiry`
**HEAD:** `1e8d5c8`
**Verification Method:** GitHub Actions CI (PostgreSQL 16 + PostGIS, full regression) + local PostgreSQL 16 verification

---

## Repository Version

| Field | Value |
|---|---|
| Repository | `tassiatmanouchehr-cloud/taasisatSeniorNew` |
| Main branch HEAD | `8910a7c` (PR #43 merge — canonical docs) |
| Active feature branch | `feature/order-offer-selection-expiry` @ `1e8d5c8` |
| Active PR | #44 (Sprint 5.2 — offer selection and hold expiration) |
| Python | 3.12+ |
| Django | 5.2 |
| PostgreSQL | 16 |

## Current Baseline

Full regression: **2,578 / 2,578 tests passing**

| Suite | Count | Status |
|---|---|---|
| OrderOffer selection tests (Sprint 5.2) | 32 | PASS |
| OrderOffer service tests (Sprint 5.1) | 29 | PASS |
| OrderOffer model tests | 40 | PASS |
| Architecture guardrail tests | 28 | PASS |
| Full regression | 2,578 | PASS |
| `manage.py check` | 0 issues | PASS |
| Visual & Accessibility (Playwright) | All | PASS |
| `git diff --check` | Clean | PASS |

## Implemented Modules

| Module | Status | Evidence |
|---|---|---|
| Multi-tenant infrastructure (Tenant, RBAC, Audit, Config, FeatureFlags) | **Complete** | 12 kernel models, 12 services, 40 permission keys |
| User registration (customer/caregiver/company) | **Complete** | Phone/OTP flow, 3 registration paths |
| Identity document verification | **Complete** | Upload, review (approve/reject/correction), rollup |
| Profile activation lifecycle | **Complete** | DRAFT→ACTIVE, eligibility checks, ServiceSupplier sync |
| Company-caregiver affiliation | **Complete** | Join-by-code, invitation, termination, immutable history |
| Caregiver professional profile | **Complete** | Skills, experience, gallery, availability, dashboard |
| Organization professional profile | **Complete** | Headline, logo, public directory, staff management |
| Customer portal | **Complete** | Orders, payments, reviews, favorites, care recipients, wizard |
| Public marketplace | **Complete** | Caregiver/org directories, search, profiles, tenant resolution |
| Order lifecycle (7-state machine) | **Complete** | All transitions implemented |
| Supplier matching | **Complete** | MatchOrchestrator, eligibility, ranking |
| Supplier assignment | **Complete** | Assignment lifecycle, confirm/decline, organization assignment |
| Execution session tracking | **Complete** | Session lifecycle, provider/customer actions |
| Commission contracts | **Complete** | Contract lifecycle, snapshots, policy management |
| Escrow management | **Complete** | Hold, partial release, refund, movement tracking |
| Dispute resolution | **Complete** | Open, resolve, line items, release/refund instructions |
| Financial documents | **Complete** | Invoicing, document lifecycle (draft→issued→locked→paid) |
| Wallet system | **Complete** | Balance, transactions, snapshots |
| Pricing engine | **Complete** | Rules, quotes, promotions |
| Reviews and reputation | **Complete** | Submission, moderation, reputation snapshots |
| Notifications infrastructure | **Complete** | Model, dispatch service, delivery attempts |
| Background jobs | **Complete** | JobDefinition, claim/execute with skip_locked |
| REST API | **Complete** | 12 DRF endpoints |
| Admin portal | **Complete** | 20 routes, RBAC-protected |
| Visual regression testing | **Complete** | 525 baselines, 7 Playwright specs |
| RBAC enforcement-toggle visibility | **Complete** | Read-only admin page, audited management command |

## Partially Implemented Modules

| Module | Implemented | Missing |
|---|---|---|
| OrderOffer lifecycle | submit, edit, withdraw (Sprint 5.1); select, expire (Sprint 5.2) | accept, cancel (Sprint 5.3) |
| Payment collection | Intent/attempt/callback infrastructure | Real PSP adapter (only FakePaymentProvider) |
| SMS/notification delivery | Notification model + dispatch | Real SMS provider (`_send_sms()` undefined) |
| Escrow→wallet settlement | ReleaseInstruction created | No consumer wires instruction to wallet credit |
| Commission allocation | AllocationCalculator exists | Zero production callers |

## Not Yet Implemented

| Module | Dependency |
|---|---|
| Production deployment (Docker/CD/reverse-proxy) | None — can be done independently |
| Real SMS provider integration | None |
| Real payment gateway integration | None |
| Escrow release consumer (ReleaseInstruction→wallet) | Commission allocation |
| Order cancellation permission enforcement | None |
| Invoice generation workflow (Phase 6) | Offer acceptance (Phase 5 completion) |
| Financial engine review (Phase 7) | Invoice workflow |
| Payment & settlement review (Phase 8) | Financial engine |

## Known Technical Debt

| Item | Location | Impact |
|---|---|---|
| Dual wallet implementations | `finance.WalletAccount` (LEGACY/FROZEN) + `wallet.Wallet` (canonical) | Confusion risk; legacy has zero callers |
| Dead settlement code | `finance.SettlementBatch`/`SettlementItem` — can never reach APPROVED/PAID | Dead code |
| Dual role catalogs | `DEFAULT_TENANT_ROLES` (12) vs `DEV_BOOTSTRAP_ROLES` (14) | Deliberate; acknowledged in code comments |
| `DiscoveryService.search()` bypassed | Both directories call lower-level services directly | Dead code (the facade is unused) |
| RISK-009 migration drift | `kernel` app `help_text`/`verbose_name` cosmetic changes pending | No schema impact; `makemigrations --check` exits 1 |

## Known Limitations

| ID | Limitation | Impact |
|---|---|---|
| No tenant-scoping middleware | Isolation relies on per-service discipline (168 methods) | A service bug could leak cross-tenant data |
| No per-caregiver time zone | Platform-wide `Asia/Tehran` only | Multi-timezone markets unsupported |
| No flash-message framework | Failed POST actions silently redirect | Users get no error feedback |
| Gallery orphan-file cleanup not automated | Deleted gallery items may leave orphaned files on disk | Storage leak over time |
| `UniqueConstraint(order, supplier)` on offers | A supplier cannot re-offer after withdrawal | Accepted product decision |
| No automated profile deactivation | No service suspends/archives profiles when verification expires | Manual-only revalidation |

## Missing Integrations

| Integration | Purpose | Status |
|---|---|---|
| SMS provider (e.g., Kavenegar) | OTP delivery, notification dispatch | Not integrated |
| Payment gateway (e.g., Zarinpal) | Real payment collection | Not integrated |
| Object storage (e.g., S3) | Production media file serving | Not integrated (local FileSystemStorage) |
| Email provider | Email notifications | Not integrated |
| Push notification service | Mobile push | Not integrated |
| Monitoring/APM | Production observability | Not integrated |

## Security Status

| Check | Status |
|---|---|
| All portals enforce authentication | PASS |
| RBAC enforced on admin portal (11 keys) | PASS |
| Ownership-scoped access on customer/provider/org portals | PASS |
| Cross-tenant access returns 404 (non-disclosing) | PASS |
| IDOR prevention (resolve_*_profile pattern) | PASS |
| Order cancellation permission check | **FAIL** — no PermissionService.require() call |
| RBAC enforcement toggle audit trail | PASS (PR #24) |
| Immutable audit logging | PASS |

## Architecture Health

| Metric | Value | Assessment |
|---|---|---|
| Architecture guardrail tests | 28 passing | Strong enforcement |
| ORM-discipline violations in views | 0 (automated scan) | Clean |
| Circular dependencies | 0 detected | Healthy |
| Unused permission keys | 0 | Clean |
| `select_for_update()` call sites | 95 | Comprehensive locking |
| `@transaction.atomic` blocks | 159 | Consistent |
| `AuditService.log()` call sites | 51 | Good coverage |
| Concurrency test files | 12 | Strong |

## Test Status

| Metric | Value |
|---|---|
| Total test files | 263 |
| Total tests passing | 2,578 |
| Test lines of code | ~41,000 |
| Playwright visual specs | 7 |
| Visual baseline images | 525 |
| Concurrency test files (TransactionTestCase) | 13 |

## Migration Status

- 50 migrations across 15 apps
- No pending schema migrations
- RISK-009: pre-existing cosmetic metadata drift in `kernel` app (help_text/verbose_name only)
- `manage.py migrate --check`: PASS (no unapplied migrations)
- `makemigrations --check --dry-run`: exits 1 (RISK-009 only)

## CI Status

| Workflow | Status |
|---|---|
| Lint & Format Check | PASS |
| UI Quality Gates | PASS |
| Tailwind CSS Build | PASS |
| Django Test Suite | PASS (2,578/2,578) |
| Visual & Accessibility Tests | PASS |

## Next Recommended Priority

1. **Fix order cancellation permission gap** — add `PermissionService.require()` to `request_cancellation()` and `approve_cancellation()`
2. **Complete Sprint 5.3** — implement `accept_offer` (crosses into booking/assignment/financial), `cancel_offers_for_order`
3. **Integrate real SMS provider** — enable OTP delivery and notification dispatch
4. **Integrate real payment gateway** — replace FakePaymentProvider
5. **Wire escrow release consumer** — connect ReleaseInstruction to wallet credit
6. **Create production deployment infrastructure** — Dockerfile, CD pipeline, reverse proxy
