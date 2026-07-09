# Product Roadmap

Status: current as of the Customer Experience Phase 1 sprint (branch
`claude/customer-experience-phase1`), based on `main` @
`ad415cb59dc9d114c1f1c5bbe9d810a2c292497f` (PR #20's merge commit).

This roadmap is organized **by business value, not by Blueprint module
number** — the order a customer, provider, or organization experiences
value, not the order modules happen to be numbered. See
[`GAP_ANALYSIS.md`](GAP_ANALYSIS.md) for the evidence behind every gap
named here, and [`PROJECT_MODULE_STATUS.md`](PROJECT_MODULE_STATUS.md) for
the module-by-module detail.

Priority is relative, across the whole roadmap, not just within a phase:
**P0** = blocks the platform from doing its basic job (a real transaction
end-to-end), **P1** = materially improves what's already usable, **P2** =
expands into new territory once P0/P1 are solid, **P3** = enterprise-scale
concerns that only matter once there are multiple paying organizations or
external integrators.

---

## Customer Experience

**Purpose**: let a customer go from "I need care for my mother" to a
completed, paid, reviewed service without any step silently doing
nothing.

**Business Value**: this is the core transaction loop the entire platform
exists to support. Every other phase either serves this one or depends on
it existing first.

**Features**:
- Customer Selection — let a customer actually choose among matched
  candidates (Matching currently has no accept step for the requester).
- Real order-status notifications (SMS/email/push, not console logs).
- ~~`CareRecipient` + Order Share Link~~ — **done** (Customer Experience
  Phase 1): a customer manages care for father/mother/spouse without a
  second account (`ElderProfile`, extended per ADR-008), and a family
  member can follow one order via a revocable, time-limited link without
  one either (`OrderShareLink`). Also delivered in the same sprint: a
  customer dashboard, care recipient CRUD, a service request wizard
  reusing existing pricing/order/matching services, an order timeline
  reusing `OrderStatusHistory`, and a notification center reusing
  `apps.notifications` — all under the new `apps.portal` app.
- Geo-aware search and proximity-based discovery.
- Real payment methods at checkout, with a payment that actually resolves
  to a settled, wallet-reflected transaction.

**Modules involved**: 01 (Request), 02 (Matching), 05 (Financial Ops), 09
(Search/Discovery), 10 (Geospatial), 12 (Communication).

**Dependencies**: Financial settlement bridge (Production phase), real
communication providers (Production phase), Geospatial foundation (no
dependency — can start independently).

**Expected Result**: a customer can complete a real request end-to-end,
know what's happening at every step, and pay for it through a method that
actually moves money.

**Priority**: **P0** — this is the product.

---

## Provider Experience

**Purpose**: let a caregiver or organization actually work the platform,
not just be selectable inside it.

**Business Value**: matching is worthless if the matched provider never
gets to act on it. Reputation is worthless if a provider can never appeal
an unfair review.

**Features**:
- Candidate accept/decline workflow for Matching.
- Execution evidence capture (photos, notes) during service delivery.
- Reputation depth — appeals and abuse prevention, and fixing the known
  reviewer-ownership integrity gap (see `GAP_ANALYSIS.md`).
- Calendar-grade availability tooling on top of the existing
  `availability` data model.

**Modules involved**: 02 (Matching), 03 (Booking), 04 (Execution), 13
(Document/Media), 14 (Review/Reputation).

**Dependencies**: Document/Media foundation (needed for execution
evidence); the reviewer-ownership fix has no dependency and can ship
immediately.

**Expected Result**: a provider can accept work, prove they did it, and
trust that their reputation reflects only real, legitimate reviews.

**Priority**: **P1** — the platform functions without this today only
because an operator manually assigns work; this phase is what makes it
self-serve for providers.

---

## Organization Experience

**Purpose**: let a care organization (an agency employing multiple
caregivers) actually manage its business on the platform, not just exist
as a single admin account.

**Business Value**: organizations are a distinct, higher-value customer
segment (agencies bring many caregivers and recurring volume) that the
current foundation only partially serves.

**Features**:
- `Branch`/`Department`/`Team` model — frozen in the Phase 0.5 domain
  model, never built.
- Organization-level dashboards and reporting.
- Bulk caregiver management and deeper affiliation-request workflows.

**Modules involved**: 08 (Identity/Access — organization structure), 17
(Analytics/Reporting).

**Dependencies**: none blocking — this can start as soon as it's
prioritized against Customer/Provider Experience work.

**Expected Result**: an organization admin can operate a multi-caregiver
business on the platform, not just be one account among many.

**Priority**: **P1** — real, deferred value; not blocking the core
transaction loop.

---

## Platform Operations

**Purpose**: give the people running the platform day to day the tools
that already-built infrastructure implies but doesn't yet expose.

**Business Value**: every hour spent operating this platform by hand
(seeding permissions in a shell, checking a database directly instead of
a dashboard) is an hour of avoidable operational cost, and a source of
mistakes.

**Features**:
- Give the admin portal write capability — it is strictly read-only
  today.
- Real background job handlers — outbox processing, payment-intent
  expiry, wallet reconciliation, reporting refresh (the `apps.jobs`
  infrastructure is done; almost nothing runs on it).
- Metrics and alerting beyond a single health-check endpoint.
- A config/feature-flag admin UI on top of the existing `ConfigResolver`/
  `FeatureFlag` primitives.

**Modules involved**: 19 (Config/Flags), 22 (Background Jobs), 23
(Observability).

**Dependencies**: none blocking each other; can proceed in parallel.

**Expected Result**: operating the platform stops requiring direct
database/shell access for routine tasks.

**Priority**: **P1** — not customer-visible, but every other phase moves
faster once this exists.

---

## Trust & Compliance

**Purpose**: give the platform a real answer to "what happens when
something goes wrong" — a bad actor, a dispute, a fraudulent claim.

**Business Value**: the regulatory and reputational cost of deferring
this grows with every real user on the platform, not with every sprint of
development time. This is the phase most likely to become urgent
suddenly rather than gradually.

**Features**:
- Trust & Governance engine — `TrustCase`, disputes, appeals, fraud
  signals (currently zero code exists for any of this).
- Fix the review reviewer-ownership integrity gap.
- Consent records (the `CareRecipient` model itself now exists as
  `ElderProfile`, per ADR-008/Customer Experience Phase 1; consent
  records on top of it remain unbuilt).
- Audit/observability depth sufficient to serve as regulatory evidence.

**Modules involved**: 06 (Trust/Governance), 14 (Review/Reputation), 23
(Observability).

**Dependencies**: Observability improvements (Platform Operations phase)
strengthen this phase's audit-evidence story but aren't strictly
blocking.

**Expected Result**: a real complaint, dispute, or fraud signal has a
documented, auditable path through the platform instead of no path at
all.

**Priority**: **P1**, trending toward **P0** the longer real users exist
on the platform without it.

---

## AI

**Purpose**: use the data the platform is accumulating to make matching,
search, and operational decisions smarter than fixed rules.

**Business Value**: real, but not realizable yet — recommendations need
ranking signals (reviews feeding matching, which today are hardcoded to
zero) and location data (which doesn't exist) to have anything meaningful
to learn from.

**Features**:
- Provider-matching recommendations, once ranking signals are real.
- Search relevance improvements, once Search/Discovery has depth beyond
  its current foundation.

**Modules involved**: 09 (Search/Discovery), 17 (Analytics/BI), 20
(AI/Recommendation).

**Dependencies**: **Hard dependency** on Search/Discovery depth,
Geospatial foundation, and Analytics/BI maturity — none of which exist
yet. Starting Module 20 before these exist would mean building a
recommendation engine with nothing real to recommend from.

**Expected Result**: not applicable until dependencies mature. This
phase's near-term "result" is intentionally: not started, and correctly
so.

**Priority**: **P3** — genuinely not urgent; starting early would be
wasted effort against a moving foundation.

---

## Production

**Purpose**: replace every documented fake with something real, so the
platform can safely handle a real customer's money, phone number, and
identity.

**Business Value**: this is the gate between "an impressive, well-tested
demo" and "a system real people can use." Every item here is a fake
provider or missing bridge that today silently does nothing, rather than
failing loudly — the most dangerous kind of gap to leave in place.

**Features**:
- A real PSP adapter (Zarinpal, Mellat, Stripe, or similar) with
  signature/HMAC callback verification.
- A real SMS/email/push provider.
- The payment-settlement bridge (`PaymentIntent` → wallet credit /
  `finance.PaymentTransaction`).
- Permission-key registry and default-role permission seeding for real
  tenants (today, a fresh deployment's RBAC-gated features are silently
  inert).
- Reconcile the two parallel async-execution mechanisms
  (`apps.jobs` vs. the Celery/`EventOutbox` worker) into one documented
  story.
- An OpenAPI schema, before any external API consumer exists to need
  one.

**Modules involved**: 05 (Financial Ops), 08 (Identity/Access), 12
(Communication), 18 (API Gateway), 22 (Background Jobs).

**Dependencies**: none of these block each other; several (real SMS
provider, permission registry) can ship independently and immediately.

**Expected Result**: the platform can be deployed for real users without
anyone discovering, in production, that a "payment succeeded" never
actually moved money or that a "notification sent" never reached anyone.

**Priority**: **P0** — this phase is what makes every other phase's work
actually matter to a real user.

---

## Enterprise

**Purpose**: support multiple paying organizations, external
integrators, and markets beyond the current single Persian-language
deployment.

**Business Value**: real, but only realizable after Production and
Customer/Provider Experience are solid — selling to a second tenant or
opening a public API before the core loop is trustworthy multiplies risk
rather than revenue.

**Features**:
- Public API Gateway — partner integrations, outbound webhooks, API
  keys, throttling (the internal API foundation already exists; the
  gateway/partner half does not).
- Subscription, Plans & Licensing — needed before selling to multiple
  organizations commercially with differentiated tiers.
- A true multi-locale i18n framework — needed before expanding past
  Persian-only.
- Exercising the white-label/multi-tenant depth already designed into
  the data model (frozen in Phase 0.5) but never product-tested with a
  second real tenant.

**Modules involved**: 18 (API Gateway), 21 (Subscription/Licensing), 24
(i18n).

**Dependencies**: **Hard dependency** on the Production phase — none of
this should ship before real payments, real notifications, and real RBAC
enforcement exist, since Enterprise features multiply the platform's
exposure to exactly those gaps.

**Expected Result**: the platform can be sold to and operated by more
than one organization, with real external integrations, in more than one
language.

**Priority**: **P2** — real future value, deliberately sequenced after
Production.

---

## Summary — priority order across all phases

| Priority | Phases |
|---|---|
| **P0** | Customer Experience, Production |
| **P1** | Provider Experience, Organization Experience, Platform Operations, Trust & Compliance |
| **P2** | Enterprise |
| **P3** | AI |

This is a value-ordering, not a strict sequence — Platform Operations and
parts of Production can and should proceed in parallel with Customer
Experience work, since neither blocks the other technically. The one
genuinely hard sequencing constraint in this roadmap is **AI depends on
Search/Discovery + Geospatial + Analytics maturing first**, and
**Enterprise depends on Production landing first**.
