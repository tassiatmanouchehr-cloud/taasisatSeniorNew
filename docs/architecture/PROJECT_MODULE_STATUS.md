# Project Module Status

Status: current as of the Repository Documentation & Project Governance
sprint, `main` @ `25b5f8ec3dab673beaa4ff954c577c6338d4764f`. This is the
**permanent module inventory** — the canonical mapping between the 25
Blueprint modules (`module/MODULE_INDEX_COMPLETE_01_25.json`) and what has
actually been built in `src/apps/`.

**Every row was verified by reading source code, tests, and ADRs — not
inferred from a PR title.** "Current Test Coverage" counts test *files*
under each app's `tests/` directory (a rough proxy for depth, not a
percentage — this repository does not run coverage.py in CI today, so a
true line/branch coverage percentage is **Needs Verification**). Status
definitions:

- **Completed** — matches its Blueprint scope in full. *(No module in
  this repository currently qualifies — see the note at the bottom.)*
- **Mostly Complete** — the core capability is real, tested, and used by
  other code; meaningful but bounded pieces of the Blueprint scope remain.
- **Partial** — a real foundation exists, but it is disconnected from
  something essential (a real external provider, a completing workflow
  step, or most of the Blueprint's described scope).
- **Not Started** — no model, service, or meaningful code exists for this
  module's domain.

A module's Blueprint number and PR label frequently **do not match** — see
`PROJECT_STATE.md` → *A note on module numbering*. The "Implementation
PR(s)" column uses this repository's actual merged PR numbers; "pre-PR"
means the work shipped as a direct commit before the PR-per-module
workflow began (visible in `git log` as a "Sprint" commit with no `Merge
pull request` entry).

---

<div style="overflow-x:auto">

| # | Blueprint Module | Purpose | Status | Repository App(s) | Implementation PR(s) | Merge Commit | Test Coverage | Architecture Notes | Remaining Work | Dependencies | Recommended Future Module |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | Request Engine | Service request intake, draft/submission lifecycle, requester context | **Not Started** | — (`apps.orders.Order` proxies for it, by explicit documented substitution — ADR-002) | — | — | 0 test files (proxy: `orders` has 4) | `Order` plays this role today; ADR-002 states this is a deliberate, temporary simplification, not a permanent coupling. | Split a real `Request`/`RequestServiceNeed` aggregate out of `Order`. | `kernel` | Request Engine Extraction |
| 02 | Matching Engine | Provider eligibility, ranking, availability checks, candidate generation | **Partial** | `matching` | pre-PR (Sprint 4A) | `6ce6c9b` | 6 files | ADR-002: "minimal, honest subset." Matching only proposes — never writes `Order.assigned_supplier`. Zero `PermissionService` references found in `apps.matching` (confirmed by search) — RBAC is not enforced on `matching.*` operations. | Customer-selection flow, candidate accept/decline, RBAC enforcement, reputation-driven ranking (score is hardcoded 0 today), org-affiliation-aware eligibility. | `kernel`, `orders` | Matching Engine Hardening |
| 03 | Booking, Assignment & Service Activation Engine | Booking lifecycle, provider assignment, acceptance, scheduling, activation | **Mostly Complete** | `booking` | pre-PR (Sprint 5A) | `c57e999` | 9 files | `SupplierAssignment` is explicitly *not* the source of truth for the current assignment — `Order.assigned_supplier` is. | Reassignment/conflict-handling depth, richer activation rules. | `matching`, `orders` | Booking Lifecycle Expansion |
| 04 | Service Execution Engine | Service delivery lifecycle, check-in/out, execution evidence, exceptions | **Partial** | `execution` | pre-PR (Sprint 6A) | `dfb7347` | 9 files | `ExecutionSession` layered on `Order.status`; never mutates `Order` fields directly. | Execution evidence/media capture, OCR (belongs to Module 13, not started). | `booking`, `orders` | Execution Evidence & Media |
| 05 | Financial Operations Engine | Ledger, wallet, payments, commissions, settlement, reconciliation | **Mostly Complete** | `finance`, `wallet`, `payments` | #2/#3 (finance), #10 (wallet), #11 (payments) | `a9ac8cd`, `186871b`, `8378dd5` | 17 + 6 + 7 = 30 files | Deepest subsystem in the repository. `apps.finance.models.wallet` is legacy/frozen (ADR-004, guardrail-enforced). `PaymentIntent` and `finance.PaymentTransaction` are deliberately separate (ADR-005) and **not yet bridged**. | Wire a successful `PaymentIntent` to a wallet credit / `finance.PaymentTransaction`; real PSP adapters; commission/payout automation; reconciliation. | `orders`, `execution` | Payment Settlement Bridge |
| 06 | Trust, Compliance & Governance Engine | Trust controls, disputes, appeals, fraud signals, moderation | **Not Started** | — (`apps.reviews` has a moderation-status sliver, borrowed by proximity) | — | — | 0 dedicated files | No `TrustCase`, dispute, appeal, or fraud-signal model exists anywhere. | Everything — `TrustCase`, dispute/appeal workflow, fraud signals, compliance evidence. | `reviews`, `orders`, `finance` | Trust & Governance Engine |
| 07 | Communication Orchestration Engine | Decide who/when/what/which-channel for a message; business modules never send directly | **Partial** | `kernel` (hardcoded handlers in `apps.kernel.events.handlers`) | #4/#5 (Sprint 09 branch) | `4ecb274`, `fad3c60` | shared with kernel's 17 | **Naming note**: the Blueprint index JSON mislabels this module "Business Roles & Platform Structure" — the Intake Report corrects this to Communication Orchestration; "Business Roles" content merged into Module 08. Today's "orchestration" is five hardcoded `if event_type ==`-shaped handlers, not a configurable rules engine. | Configurable orchestration rules, message templates, user preferences, channel routing. | Module 12, Module 19 | Communication Orchestration Rules |
| 08 | Identity, Roles, Profiles & Access Engine | Identity, auth, profiles, role assignment, permissions, org affiliation | **Mostly Complete** | `kernel`, `accounts` | #3 (RBAC), #19 (auth UX/multi-role) | `8cf5442`, `870ddad` | kernel 17 + accounts 9 = 26 files | The most mature demand-side subsystem. Email is now the Django-admin login identifier (`USERNAME_FIELD`), UUID no longer exposed as one. Multi-role identity via idempotent `ensure_*_profile()` helpers, no duplicate accounts. | No permission-key registry (freeform strings); default seeded roles ship with empty `permissions` generally (fixed for the dev `platform-owner` specifically, not fixed platform-wide); OTP delivery is console-only. | — (foundational) | RBAC Hardening & Permission Registry |
| 09 | Search, Discovery & Filtering Engine | Marketplace discovery, keyword search, filters, facets, ranking | **Partial** | `discovery` | #8 (branch labeled "module-12") | `34d8ca2` | 6 files | Owns no models — pure service layer over other apps' data. | Full-text search engine, faceted filters, geo-aware discovery (blocked on Module 10 not existing). | Module 10 | Search Engine Upgrade |
| 10 | Geospatial, Maps & Location Engine | Addresses, geocoding, distance/ETA, geofencing, service areas | **Not Started** | — | — | — | 0 files | Confirmed by full-tree search: no lat/long fields, no geocoding, no distance/ETA logic anywhere. Only an unused `GIS_ENABLED` settings flag (conditionally installs `django.contrib.gis`) exists. | Everything — addresses, geocoding, distance matrix, service-area/geofencing, live-location privacy. | `kernel` | Geospatial Foundation |
| 11 | Incentives, Referrals, Promotions & Commission Policy Engine | Referral programs, campaigns, incentives, reduced commissions, reward lifecycle | **Partial** | `pricing` (partial overlap only) | #7 (branch labeled "module-11-pricing") | `ec566dc` | 7 files | `apps.pricing` has real `PricingRule`/`Promotion`/`Quote` — general pricing, not this module's actual namesake (referral programs, campaigns, reward lifecycle, fraud prevention), none of which exist. | Referral programs, campaigns, reward lifecycle, fraud prevention, settlement integration. | Module 05, Module 08 | Referral & Incentives Program |
| 12 | Communication & Notification Engine | Email, SMS, push, voice, chat, in-app inbox, templates, delivery governance | **Partial** | `notifications` | #4/#5 (creation, branch "module-09"), #18 (dispatch) | `4ecb274`, `c978b01` | 4 files | Real dispatch pipeline: retry/backoff, dead-letter, `NotificationDeliveryAttempt` audit trail. Every provider is fake (`FakeSmsProvider`, `FakeEmailProvider`, `FakePushProvider`, `FakeInAppProvider`) — confirmed by full-tree search, no real SDK (Twilio/SendGrid/Kavenegar/etc.) exists. | Real SMS/email/push provider(s), templates, user preferences, in-app inbox UI, voice/chat. | Module 07, Module 22 | Real Provider Integration |
| 13 | Document, Media & File Management Engine | Secure file ingestion, versions, previews, malware scanning, retention | **Not Started** | — | — | — | 0 files | No `Document`/`MediaAsset` model, no storage abstraction, no malware scanning, no OCR anywhere. One early frontend-only "file upload UI components" commit exists with no backend behind it. | Everything — ingestion, storage abstraction, versions, permissions, retention. | `kernel`, `orders`, `execution` | Document & Media Foundation |
| 14 | Review, Rating & Reputation Engine | Verified reviews, ratings, reputation scores, moderation, appeals | **Mostly Complete** | `reviews` | #9 (branch labeled "module-13") | `d1d5fd5` | 6 files | Tenant-isolated, tested. **Known bug**: `ReviewSubmissionService.submit_review()` never verifies the reviewer is the order's actual customer — any authenticated user with `reviews.submit` in-tenant can review any completed order. Documented in `technical-debt-register.md`, not fixed. | Fix the reviewer-ownership gap; abuse prevention; appeals workflow. | `orders`, `execution` | Review Integrity Fix + Appeals |
| 15 | Knowledge, CMS & Content Engine | Headless content, help center, policies, landing pages, versioning, approvals | **Not Started** | `public_site`, `showcase` (static presentation only) | pre-PR | `02d9570` (initial import) | 0 files (by design — no logic to test) | Confirmed: server-rendered marketing pages with zero backend content model. No versioning, no approval workflow, no help-center data model. Not a CMS — a static shell that happens to render content. | Real headless content model, versioning, approvals, help center. | `kernel` (RBAC for authors) | Headless CMS |
| 16 | Workflow & Automation Engine | Event-triggered workflows, approvals, timers, escalations, human tasks | **Not Started** | — (`apps.jobs` is a *different* concern — cron-like job execution, not stateful workflow) | — | — | 0 files | Explicitly distinguished from Module 22: `apps.jobs` runs a fire-and-forget unit of work; this module is a stateful, no-code, event-triggered workflow/approval engine. Neither exists as the other. | Everything — stateful workflows, approvals, escalations, human tasks. | Module 22, Module 25 events | Workflow Automation Engine |
| 17 | Analytics, Reporting & BI Engine | Metrics, dashboards, funnels, cohorts, exports, semantic layer | **Partial** | `reporting` | #12 (branch labeled "module-16") | `abea539` | 7 files | ADR-006: deliberately models-less, every report computed live via ORM `aggregate()`/`annotate()`, DTOs only, no caching. | Materialization/caching, funnels, cohorts, scheduled exports, semantic layer. | All business apps | BI & Materialized Reporting |
| 18 | Integration & API Gateway Engine | Public/private APIs, webhooks, partner integrations, throttling, contract governance | **Partial** | `api` | #13 (foundation), #14 (public endpoints) | `7c9f4b9`, `7e61e02` | 14 files | ADR-003/ADR-007: real DRF, thin-controller-guardrail-enforced. 5 domains, ~9 endpoints, internal-only. | Public/partner API surface, outbound webhooks, API keys/credentials, throttling, OpenAPI schema (`drf-spectacular` installed, unused). | Module 08, Module 25 | Public API Gateway |
| 19 | Platform Configuration & Feature Flag Engine | Tenant-aware config, feature flags, rollout, experiments, kill-switches | **Partial** | `kernel` (`ConfigResolver`, `FeatureFlag` models) | pre-PR (early kernel foundation) | — | shared with kernel's 17 (includes `test_feature_flags.py`, `test_policy.py`) | Low-level primitives are real and tested. No admin UI, no experiment/rollout wiring, no feature in the codebase actually gates on a flag today. | Admin UI, experiment/rollout wiring, real kill-switch usage by at least one feature. | Module 25, Module 08 | Config & Flags Admin UI |
| 20 | AI & Recommendation / Decision Intelligence Engine | Recommendations, ranking, predictions, model governance, explainability | **Not Started** | — | — | — | 0 files | Confirmed by full-tree search: zero AI/ML/embedding/LLM-integration code anywhere. | Everything. | Module 09, Module 17 | AI Recommendation Engine |
| 21 | Subscription, Plans & Licensing Engine | Plans, quotas, entitlements, usage metering, billing integration | **Not Started** | — | — | — | 0 files | Confirmed by full-tree search: no `Plan`/`Subscription`/quota/entitlement model anywhere. | Everything. | Module 05, Module 08 | Subscription & Licensing Engine |
| 22 | Background Jobs & Scheduler Engine | Queues, workers, delayed jobs, cron, retries, dead-letter queues | **Mostly Complete** | `jobs` | #17 (branch labeled "module-20") | `2e3e07f` | 1 file | Real, tested infrastructure — `JobDefinition`/`JobRun`, registry, retry/backoff, dead-letter, `run_due_jobs`. Deliberately built without Celery/Redis, even though a separate Celery/EventOutbox worker also exists in `kernel.tasks` (see `GAP_ANALYSIS.md` — two parallel async mechanisms). | Register real business handlers (outbox processing, payment-intent expiry, wallet reconciliation, reporting refresh) — only `notifications.dispatch_pending` exists today, and it dispatches to fake providers. | Whichever module needs async work | Real Job Handlers |
| 23 | Observability, Monitoring & Health Engine | Logs, metrics, traces, health checks, alerts, SLOs, runbooks | **Partial** | `kernel` (`apps.kernel.api.health`, `AuditService`) | pre-PR | — | shared with kernel's 17 | A DB/cache health-check endpoint and a structured audit log exist. | Metrics, traces, alerting, SLOs, incident runbooks, dashboards beyond the admin portal's single system-status page. | Module 25 | Observability Stack |
| 24 | Internationalization & Localization Engine | Languages, regions, currencies, timezones, calendars, translations | **Partial** | UI layer (`ui/`, `templates/`) — no dedicated app | pre-PR (Sprint 3A.1) | `4f48d40` (and siblings) | `src/locale/` contains only `.gitkeep` — confirmed empty, no `.po` translation files exist | Deep, genuine RTL + Jalali-calendar work — but a single hardcoded locale (Persian/Iran), not a switchable multi-locale framework. No currency abstraction beyond IRR hardcoded in `wallet`. | A true multi-locale framework: translation files, currency abstraction, per-tenant locale/timezone/calendar switching. | Module 19 | Multi-locale Framework |
| 25 | Platform Kernel, Shared Contracts & Cross-Module Architecture | Shared kernel, canonical identifiers, naming conventions, dependency rules, ADRs, freeze governance | **Mostly Complete** | `kernel`, `common`, `docs/adr/`, `docs/architecture/` | #15 (architecture consolidation) + ongoing kernel work | `457dd05` | kernel 17 + common 0 (tested indirectly via every app that inherits its base models) | The best-maintained part of the system: ADR-001 freeze, 8 as-built ADRs, 8+ living architecture docs, automated guardrail tests. | No permission-key registry (see Module 08); some Phase 0.5-frozen entities never built (`Branch`, `Department`, `Team`, `Capability`/`Skill`/`Certification`). | — | Kernel Hardening |

</div>

---

## Rollup

| Status | Count | Modules |
|---|---|---|
| Completed | 0 | — |
| Mostly Complete | 6 | 03, 05, 08, 14, 22, 25 |
| Partial | 11 | 02, 04, 07, 09, 11, 12, 17, 18, 19, 23, 24 |
| Not Started | 8 | 01, 06, 10, 13, 15, 16, 20, 21 |

6 + 11 + 8 = 25 — every Blueprint module is accounted for exactly once.

**No module qualifies as "Completed."** This is expected, not a defect:
every Blueprint module's spec package (80–220KB) describes substantially
more than any product needs on day one. "Mostly Complete" is the
practical ceiling for a module that is genuinely production-usable today.

See [`GAP_ANALYSIS.md`](GAP_ANALYSIS.md) for what each status actually
means in terms of business risk, and
[`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md) for what to build next, grouped
by who benefits rather than by module number.
