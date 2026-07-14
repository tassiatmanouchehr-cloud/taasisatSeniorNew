# Bounded Contexts

Status: current as of Module 18. Each section: what the app owns, what it
explicitly does not own, and its public service surface.

## kernel

Owns: `Tenant`, `Person`, `UserAccount` (auth), RBAC (`Role`,
`RoleAssignment`, `PermissionService`), `ServiceSupplier` (generic
supply-side identity), `ConfigResolver`/`ConfigurationKey`/
`ConfigurationValue`, `DomainEvent` + `EventOutbox` (two separate event
systems — see `event-architecture.md`), `AuditService`.

Does not own: any operational/business-specific data. `kernel` is the
platform foundation every other app depends on; it depends on nothing
except `apps.notifications` (one deliberate, guarded exception — see
`dependency-graph.md`).

Key services: `PermissionService`, `SupplierRegistry`/`SupplierResolver`,
`ConfigResolver`, `EventPublisher`, `AuditService`.

## accounts

Owns: `CustomerProfile`, `CaregiverProfile`, `OrganizationProfile`,
`OrganizationMembership`, `CompanyAffiliationRequest`, `ElderProfile`,
`TrustedContact`, `PlatformTeamMember`.

Does not own: supplier identity for matching/booking/pricing purposes —
that's `kernel.ServiceSupplier`. `supplier_bridge.resolve_supplier_entity()`
is the one sanctioned translator from `ServiceSupplier` back to a concrete
profile, used only where the concrete type is genuinely needed (e.g. a
`city` field for Discovery's location filter).

Multi-role identity (Module 21A): one `Person`/`UserAccount` may hold
several profiles at once (e.g. a caregiver who also books care for their
own parent as a customer) — `ensure_customer_profile()`/
`ensure_caregiver_profile()` in `apps.accounts.services.profiles` attach a
profile to an *existing* account idempotently, never creating a second
`Person` or `UserAccount`. There is deliberately **no**
`FamilyMemberProfile` or other "family member" account type — see
`docs/adr/ADR-008_DEMAND_SIDE_DOMAIN_MODEL.md`. The demand side has
exactly one requester role; who a service is *for* is data
(`CareRecipient`), not a second account.

Built in Customer Experience Phase 1 (see the same ADR and
`DECISION_HISTORY.md`): `CareRecipient` as a reusable entity reachable
from `CustomerProfile` (`customer_profile.elder_profiles` — a customer
may hold several, reused across many orders over time, with its own
demographics/medical notes/addresses/emergency contacts/preferences/order
history — consent records remain unbuilt). Implemented by extending the
pre-existing `ElderProfile` model in place rather than introducing a
second model. A third party following an order uses a read-only,
single-order, revocable, time-limited Order Share Link
(`apps.orders.services.share_links.OrderShareLinkService`) rather than an
account of any kind.

## orders

Owns: `Order` (and its status machine — the only code allowed to mutate
`Order.status` is `apps.orders.services.status_machine`), `ServiceCategory`,
`ServiceType`, `OrderStatusHistory`, `OrderShareLink`.

Does not own: assignment (that's `booking`), execution (`execution`),
pricing (`pricing`).

Per `docs/adr/ADR-008_DEMAND_SIDE_DOMAIN_MODEL.md`: `Order.elder_profile`
(FK to the reusable `CareRecipient`/`ElderProfile` owned by `accounts`,
not by `orders` — this FK pre-dates Customer Experience Phase 1 and is
what made extending `ElderProfile` in place, rather than adding a new FK,
the non-duplicating choice) distinguishes the requesting customer from
who the service is for. `OrderShareLink` (owned by `orders`, not
`accounts`) gives a non-account third party read-only, single-order,
revocable, time-limited access to follow one specific order.

## matching

Owns: `MatchRound`, `MatchCandidate` — eligibility evaluation and ranking
to produce assignment candidates. Read/propose only; it never assigns a
supplier itself (that's `booking.AssignmentService`, which may consume a
`MatchCandidate`).

## booking

Owns: `SupplierAssignment` — the operative record of "this supplier is
committed to this order." The only code that mutates `Order
.assigned_supplier`.

## execution

Owns: `ExecutionSession` — the on-the-ground delivery lifecycle layered on
top of an `Order`+`SupplierAssignment`. `close_session()` is the only code
that transitions `Order.status` to `completed`.

## finance

Owns: `FinancialParty` (the generic financial-counterparty abstraction —
also used by `wallet` and `payments`), `FinancialDocument`
(invoice/credit-note lifecycle), `PaymentTransaction` (a **post-hoc
settlement ledger entry**, not a payment gateway — see
`wallet-finance-boundary.md`), `FinancialObligation`, `LedgerEntry`,
`SettlementBatch`. Also contains the legacy, explicitly frozen
`WalletAccount`/`WalletTransaction` (Module 05) — see
`wallet-finance-boundary.md`.

Does not own: real payment collection (that's `payments`), customer stored
value (that's `wallet`).

## notifications

Owns: `Notification` rows. Created exclusively by handlers registered in
`apps.kernel.events.handlers` (Module 09) reacting to `DomainEvent`s.
Delivery (actually sending an email/SMS/push) is explicitly out of scope —
rows are created with `status=PENDING` and nothing dispatches them yet.

## availability

Owns: `ProviderWorkingWindow`, `AvailabilityBlockedPeriod`, `CapacityRule`
— when and how much capacity a supplier has.

## pricing

Owns: `PricingRule`, `Promotion`/`PromotionCondition`/`PromotionEffect`,
`Quote`/`QuoteLine` — deterministic, persisted price computation.
`QuoteService.generate_quote()` always persists (no side-effect-free
calculation path exists yet — Discovery's ranking deliberately excludes
price for exactly this reason, see `apps/discovery/services
/ranking_service.py`'s own docstring).

## discovery

Owns no models. A pure read-side orchestration
(normalize → filter → rank → paginate) over `kernel.ServiceSupplier` +
`reviews.ReputationSnapshot`/`ServiceSupplier.reputation_score`.

## reviews

Owns: `Review`, `ReviewRating`, `ReputationSnapshot`. Writes through to
`ServiceSupplier.reputation_score` on approval (the field was reserved for
this module since Module 05). See the reviewer-ownership gap noted in
`technical-debt-register.md`.

## wallet

Owns: `Wallet`, `WalletTransaction`, `WalletBalanceSnapshot` — the
**canonical** internal-stored-value ledger (Module 14). See
`wallet-finance-boundary.md` for why `finance`'s own wallet models still
exist but are frozen/legacy.

## payments

Owns: `PaymentIntent`, `PaymentAttempt`, `PaymentCallback` — a
provider-agnostic, pre-settlement payment orchestration state machine.
Explicitly does not create `Wallet`/`WalletTransaction` or
`finance.PaymentTransaction` rows — that wiring is deferred. See
`wallet-finance-boundary.md`.

## reporting

Owns no models. Pure read-side aggregation (`OperationalReportService`,
`ProviderReportService`, `FinancialReportService`, `MarketplaceReportService`)
returning immutable frozen-dataclass DTOs, never ORM objects.

## api

Owns no domain models. The `/api/v1/` DRF surface: routing, serializers
(transport shape only), the shared exception handler/error envelope,
pagination utilities, and auth/RBAC utility hooks. See `api-guidelines.md`.
