# Technical Debt Register

Status: current as of Module 18. Each entry: what it is, why it exists,
what the risk is, and what would resolve it. This register documents debt
— per this sprint's constraints, it does not fix any of it unless marked
"Resolved in Module 18" below.

## Pre-existing `accounts`/`kernel` migration drift

**What**: `python manage.py makemigrations --check --dry-run` reports
pending changes for `apps.accounts` and `apps.kernel` on every run since
Module 13 — cosmetic `Alter field`/index-rename operations (help_text,
choices metadata, manager changes) with no real schema difference.
Running `makemigrations` for real regenerates a phantom
`kernel/migrations/0010_alter_useraccount_managers_and_more.py` that must
be deleted, and any new app's migration's `dependencies` must be
corrected to reference the last real migration instead.

**Why**: Django version-skew artifact — `manage.py migrate` always
reports "no migrations to apply" for these, confirming there's no actual
drift, just a `makemigrations`-detection quirk.

**Risk**: Low. Purely a developer-experience annoyance (must remember to
clean up the phantom file after every `makemigrations <newapp>` call).
Documented as a recurring gotcha since Module 13; every module since has
handled it correctly.

**Resolution**: Would require pinning/upgrading Django and regenerating a
clean baseline migration — out of scope for a documentation sprint, and
risky (touches schema history) for a "do not create migrations unless
critical" sprint.

## Legacy frozen Finance wallet

**What**: `apps.finance.models.wallet.WalletAccount`/`WalletTransaction`
+ `apps.finance.services.wallet_service.WalletService` — a complete,
tested, but entirely unused (outside its own tests) wallet
implementation from Module 05.

**Why**: Superseded by `apps.wallet` (Module 14) once real customer-wallet
requirements (overdraft, idempotency, PROMOTION/MANUAL types) emerged.
See `wallet-finance-boundary.md` and ADR-004.

**Risk**: Low but real — a future developer could accidentally import the
legacy `WalletService` instead of the canonical one. Mitigated by the
in-code docstring markers and, as of this sprint, an automated guardrail
(`NoDuplicateWalletModelTest`) that fails if a *third* wallet model ever
appears.

**Resolution**: Deleting the legacy models would require a real migration
(dropping tables) and touching Finance — explicitly out of scope for this
sprint and probably not worth doing until/unless Finance is refactored for
an unrelated reason.

## `ReviewSubmissionService` reviewer-vs-order-customer ownership gap

**What**: `ReviewSubmissionService.submit_review()` verifies the order is
`COMPLETED`, has an assigned supplier, and isn't already reviewed for that
supplier — but never verifies `reviewer_person_id` is actually the
order's own `customer_profile.person_id`. Any authenticated user in the
same tenant with the `reviews.submit` permission can submit a review
attributed to themselves for *any* completed order in that tenant, not
just their own.

**Why**: Not caught until Module 17B's Phase 1 inspection, when a real API
endpoint made the gap externally reachable for the first time. Flagged
then, not fixed — the task explicitly scoped that module to API plumbing,
not domain-service changes, and this check is a business rule that
belongs in the service, not the API view.

**Risk**: Medium in a production deployment (reputation/review integrity),
low today (no real API consumers yet, and every RBAC-guarded endpoint
still requires a valid tenant grant to reach it at all).

**Resolution**: Add an explicit check in `ReviewSubmissionService
.submit_review()` — `order.customer_profile.person_id ==
reviewer_person_id` (or an equivalent "trusted contact" allowance if the
product wants delegated reviewing) — as a small, targeted domain-service
change in a future module.

## Fake payment callback signature/HMAC deferred

**What**: `POST /api/v1/payments/callbacks/fake/` requires no
authentication, scoped only by knowledge of the unguessable
`provider_reference` token and hard-restricted to `PaymentProvider.FAKE`
attempts.

**Why**: Deliberate — it simulates an external PSP webhook, which in
production carries no Django session. Real PSP integration (with
signature/HMAC verification) is explicitly out of scope for Module 15/17B.

**Risk**: None today — no real PSP provider exists, so this endpoint can
only ever affect `FAKE`-provider test data.

**Resolution**: When a real PSP adapter is added, its callback endpoint
must verify a provider-specific signature before calling
`PaymentCallbackService.process_callback()` — this fake endpoint should
not be reused as a template for that without adding it.

## DRF/OpenAPI schema expansion deferred

**What**: `drf-spectacular` is a declared dependency
(`requirements/base.txt`) and importable, but unused — no schema
generation, no `/api/v1/schema/` endpoint.

**Why**: Module 17A judged it unnecessary for a two-endpoint foundation;
Module 17B didn't revisit it (out of its stated scope).

**Risk**: None functionally. Growing API-consumer friction as the surface
grows without machine-readable documentation.

**Resolution**: Wire `drf-spectacular`'s `SpectacularAPIView`/
`SpectacularSwaggerView` into `apps/api/urls.py` and add
`DEFAULT_SCHEMA_CLASS` to `REST_FRAMEWORK` settings — low-risk, additive,
a good candidate for a future module once the API surface is larger.

## Real PSP providers deferred

**What**: `apps.payments.providers` contains only `FakePaymentProviderAdapter`.
`PaymentProviderRegistry` maps `PaymentProvider.FAKE` to it; no other
provider is registered.

**Why**: Explicitly out of scope for every payments-related module so far
("No real PSP integration," repeated in Modules 15, 17B, and this one).

**Risk**: None today (nothing depends on a real provider existing).

**Resolution**: Add a new adapter class per provider (Zarinpal, Mellat,
Stripe, ...) implementing the same `request_payment()`/`verify_callback()`
shape, register it in `PaymentProviderRegistry._adapters`, add real
credential handling (out of `apps.payments` — belongs in secrets/config
management) and signature verification for its callback route.

## Reporting materialization deferred

**What**: `apps.reporting` computes every report live via ORM
`aggregate()`/`annotate()` on every call — no caching, no scheduled
materialization, no background jobs.

**Why**: Explicit constraint since Module 16 ("No cached reporting layer
yet. No background materialization.").

**Risk**: Low today (dataset sizes are small in this codebase's current
state); would become a real performance concern under production load
with large per-tenant datasets.

**Resolution**: If/when needed, introduce a materialized-view or
periodic-snapshot pattern *additively* — the existing `ReportingService`
call sites shouldn't need to change, only their implementation.

## API base class consolidation deferred

**What**: `apps.api.views.base.ApiView(APIView)` exists and every view
subclasses it, but per-domain view modules don't share request-parsing
helpers beyond `pagination.py`/`permissions.py` — e.g. the
"resolve-IDs-from-body-into-tenant-scoped-objects" pattern in
`views/pricing.py` and `views/reviews.py` is duplicated rather than
factored into a shared mixin.

**Why**: Module 17B built a conservative, small surface (5 domains, 9
endpoints); premature abstraction over 2-3 call sites each was judged
not worth it at the time.

**Risk**: Low. Would become worth revisiting once Module 17B-style
domain endpoints multiply (Module 17C+, if it happens) and the
duplication starts to matter.

**Resolution**: Once there are ≥4-5 call sites of the same
resolve-tenant-scoped-object pattern, extract a small helper (e.g.
`resolve_tenant_object(model, id, tenant_id)`) into `apps/api/permissions
.py` or a new `apps/api/lookups.py`.

## Tenant-scoping manager inconsistency (found during this audit)

**What**: `ServiceSupplier`, `Person`, `UserAccount`, `Role`,
`RoleAssignment` (kernel), `ReputationSnapshot` (reviews),
`WalletBalanceSnapshot` (wallet), `OrganizationProfile` (accounts),
`SettlementItem` (finance), `PromotionCondition`/`PromotionEffect`
(pricing) all have a `tenant`/`tenant_id` field but use Django's plain
default `Manager`, not `TenantScopedManager`. Every current call site
already filters by `tenant_id` manually and correctly (verified across
Modules 10–17B) — this is not a live vulnerability.

**Why**: `TenantScopedManager` was introduced after these models already
existed; retrofitting it was never a blocking requirement since manual
filtering has consistently been done correctly.

**Risk**: Low today, but structurally fragile — nothing stops a future
call site from writing `ServiceSupplier.objects.get(id=x)` without a
tenant filter and silently leaking cross-tenant data. `ServiceSupplier`
is the highest-risk of these given how pervasively it's queried.

**Resolution**: Adding `objects = TenantScopedManager()` to these models
is schema-safe (managers aren't part of migrations) and low-risk, but
touches core RBAC/auth/supplier models — deliberately **not done in this
sprint** per the "do not modify domain services/schema unless critical"
constraint. Good candidate for a dedicated, carefully-tested future
module.

## Order Share Link tokens stored in plaintext

**What**: `apps.orders.models.OrderShareLink.token` is stored in
plaintext (not hashed) — an unguessable, high-entropy value
(`secrets.token_urlsafe(32)`), but the database column itself is the
credential's only protection, not a one-way hash.

**Why**: Matches the pre-existing pattern in this codebase — the fake
payment callback endpoint's `provider_reference` is handled the same way
(no signature verification, documented as a deliberate simulation of an
unauthenticated PSP webhook — see *Deferred architecture* in
`GAP_ANALYSIS.md`). Hashing the token was judged out of scope for
Customer Experience Phase 1, the same way real PSP signature
verification was deferred rather than half-built.

**Risk**: Low today (no evidence this repository has ever been exposed to
a real production database compromise scenario), but a genuine
production-hardening gap — a database read (backup leak, SQL injection
elsewhere, admin-tooling misuse) exposes usable share tokens directly,
whereas a hash would not.

**Resolution**: Store `hashlib.sha256(token).hexdigest()` instead of the
raw token, compare hashes on resolve, and return the raw token to the
caller only once at creation time — the same shape used by most
password-reset-token implementations. Not done in Customer Experience
Phase 1; a good first task for whichever future sprint hardens the fake
PSP callback's signature verification, since both are the same class of
deferred hardening.

## Resolved in Module 18

- **`apps/api/views/reporting.py` hardcoded permission string**: replaced
  the literal `"reporting.read"` with the `REPORTING_READ` constant from
  `permission_keys.py` (same value — zero behavior change).
