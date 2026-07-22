# DATA OWNERSHIP AND RELATIONSHIPS

**Last verified HEAD:** phase2-caregiver-professional-dashboard (from main @ 125dd3b, PR #9 merged)
**Last verified date:** 2026-07-15

---

## Tenant Isolation Pattern

Every business model inherits from `TenantAwareModel` (abstract) which provides:
- `tenant_id = UUIDField(db_index=True)` — NOT a ForeignKey (avoids circular deps)
- `save()` validates tenant_id is non-empty
- `TenantScopedManager.for_tenant(tenant_id)` — opt-in, not default

**Critical**: Tenant isolation depends on every service/view passing `tenant_id`. No middleware enforces it.

## Universal Abstractions

| Abstraction | Model | Purpose | Referenced By |
|-------------|-------|---------|---------------|
| Tenant | `kernel.Tenant` | Multi-tenant isolation boundary | All business models |
| Supplier | `kernel.ServiceSupplier` | Universal supply-side entity | availability, booking, matching, orders, pricing, reviews, commission |
| Financial Party | `finance.FinancialParty` | Universal financial counterparty | finance, commission, wallet, payments |
| Person | `kernel.Person` | Stable natural-person identity | accounts |
| User Account | `kernel.UserAccount` | Authentication account (AUTH_USER_MODEL) | accounts, kernel |

## Key Foreign Key Chains

### Order → All Related Entities
```
Order
├── tenant → kernel.Tenant (PROTECT)
├── customer_profile → accounts.CustomerProfile (SET_NULL)
├── elder_profile → accounts.ElderProfile (SET_NULL)
├── trusted_contact → accounts.TrustedContact (SET_NULL)
├── service_category → orders.ServiceCategory (PROTECT)
├── service_type → orders.ServiceType (SET_NULL)
├── assigned_supplier → kernel.ServiceSupplier (SET_NULL)
├── created_by → AUTH_USER_MODEL (SET_NULL)
├── reviewed_by → AUTH_USER_MODEL (SET_NULL)
└── cancellation_requested_by → AUTH_USER_MODEL (SET_NULL)
```

### Financial Document Chain
```
FinancialDocument
├── order → Order (SET_NULL)
├── execution_session → ExecutionSession (SET_NULL)
├── issuer_party → FinancialParty (PROTECT)
├── payer_party → FinancialParty (PROTECT)
└── beneficiary_party → FinancialParty (SET_NULL)

FinancialDocumentItem → FinancialDocument (CASCADE)
FinancialObligation → FinancialDocument (PROTECT)
PaymentTransaction → FinancialDocument (SET_NULL)
LedgerEntry → FinancialDocument (SET_NULL)
EscrowRecord → FinancialDocument (PROTECT)
```

### Escrow Chain
```
EscrowRecord
├── source_document → FinancialDocument (PROTECT)
├── payer_party → FinancialParty (PROTECT)
├── beneficiary_party → FinancialParty (SET_NULL)
├── order → Order (SET_NULL)
├── payment_transaction → PaymentTransaction (SET_NULL)
├── commission_snapshot → CommissionSnapshot (PROTECT, nullable)
├── UNIQUE(tenant, idempotency_key) WHERE idempotency_key != ''
└── 3 CheckConstraints (conservation, held_derived, releasable_within_remaining)

EscrowMovement → EscrowRecord (PROTECT) — immutable audit trail
```

### CaregiverProfile → Related Entities (Phase 2.1 additions in bold; Sprint 2.2 additions in italics)
```
CaregiverProfile
├── user → AUTH_USER_MODEL (CASCADE, OneToOne)
├── person → kernel.Person (CASCADE, OneToOne)
├── documents → accounts.VerificationDocument (CASCADE, reverse FK, related_name="documents")
├── **skills → accounts.CaregiverSkill (CASCADE, reverse FK, related_name="skills")**
├── **experiences → accounts.CaregiverExperience (CASCADE, reverse FK, related_name="experiences")**
└── *gallery_items → accounts.CaregiverGalleryItem (CASCADE, reverse FK, related_name="gallery_items")*

CaregiverSkill (Phase 2.1, new; is_visible actively managed since Sprint 2.3)
├── caregiver → accounts.CaregiverProfile (CASCADE)
└── UNIQUE(caregiver, name)

CaregiverExperience (Phase 2.1, new; is_visible actively managed since Sprint 2.3)
├── caregiver → accounts.CaregiverProfile (CASCADE)
└── CHECK(end_date IS NULL OR end_date >= start_date)

CaregiverGalleryItem (Sprint 2.2, new)
├── caregiver → accounts.CaregiverProfile (CASCADE)
└── INDEX(caregiver, display_order)
```
None of the three child models carries its own `tenant_id` — tenant is derived
transitively via `caregiver.user.tenant`, the same pattern `VerificationDocument` already
uses for its own caregiver/organization FKs (no `TenantAwareModel` base for any of them).
`CaregiverGalleryItem` has no unique constraint (unlike `CaregiverSkill`) — a caregiver may
legitimately upload duplicate-looking photos; ordering is enforced at the service layer
(`CaregiverGalleryService.reorder()`, row-locked), not the database.

`CaregiverSkill.is_visible`/`CaregiverExperience.is_visible` (Sprint 2.3, 2026-07-15): both
columns existed since Phase 2.1 but had no owner-facing mutation path until this sprint —
`CaregiverSkillService.toggle_visibility()` and `CaregiverExperienceService.create()`/
`update()`'s new `is_visible` parameter close that gap. No schema change — the same
columns, now actually reachable.

### ServiceSupplier → Availability Entities (Module 10 foundation; completed Sprint 2.4)

```
ServiceSupplier
├── working_windows → availability.ProviderWorkingWindow (CASCADE, reverse FK, related_name="working_windows")
├── blocked_periods → availability.AvailabilityBlockedPeriod (CASCADE, reverse FK, related_name="blocked_periods")
└── capacity_rule → availability.CapacityRule (CASCADE, reverse OneToOne, related_name="capacity_rule")

ProviderWorkingWindow (Module 10 foundation; overlap/duplicate refusal added Sprint 2.4;
concurrency-proven PR #9 review)
├── supplier → kernel.ServiceSupplier (CASCADE)
└── INDEX(tenant, supplier, day_of_week) — no DB-level uniqueness/exclusion constraint;
    overlap/duplicate prevention is enforced at the service layer
    (AvailabilityMutationService._validate_no_overlap()), not the database, matching this
    repository's existing convention for CaregiverGalleryItem's own ordering invariant.
    Concurrency-safe as of the PR #9 review: add_working_window()/update_working_window()
    lock the owning ServiceSupplier row (select_for_update()) before running
    _validate_no_overlap(), so two concurrent mutations against the same supplier's
    schedule always serialize on that one shared row — proven by 9 TransactionTestCase
    tests in apps.availability.tests.test_concurrency (see
    traceability/ARCHITECTURE_DECISION_LOG.md ADM-020's remediation note)

AvailabilityBlockedPeriod (Module 10 foundation; unchanged by Sprint 2.4)
├── supplier → kernel.ServiceSupplier (CASCADE)
└── INDEX(tenant, supplier, start_at, end_at) — overlapping blocked periods are
    deliberately allowed to coexist (harmless, pre-existing, tested behavior — see
    traceability/ARCHITECTURE_DECISION_LOG.md ADM-020 Decision 3)
```

Neither model is keyed on `CaregiverProfile`/`OrganizationProfile` directly — both key on
the generic `kernel.ServiceSupplier`, the same universal supply-side abstraction every other
availability/booking/matching concept already uses. This is the canonical, single source of
truth for a caregiver's schedule; `apps.provider_portal`/`apps.public_site` both resolve
their own `ServiceSupplier` and read through it rather than maintaining any schedule data of
their own (see `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-020 for the full ownership
decision). No new migration — both models and every field this sprint needed already existed.

## Unique Constraints (Significant)

| Model | Constraint | Purpose |
|-------|-----------|---------|
| Order | `order_number: unique=True` | Globally unique order identifier |
| OrderOffer | `(order, supplier)` unconditional | One canonical offer per supplier per order |
| OrderOffer | `(order) WHERE status='selected'` | One selected offer per order |
| CommissionContract | `(tenant, company_party, caregiver_party) WHERE status IN OPEN` | One open contract per pair |
| CommissionContract | `(tenant, company_party, caregiver_party) WHERE status='ACTIVE'` | One active contract per pair |
| Wallet | `(tenant, party, currency)` | One wallet per party per currency |
| WalletTransaction | `(wallet, idempotency_key)` | Idempotent wallet operations |
| PaymentIntent | `(tenant, idempotency_key)` | Idempotent payment creation |
| EscrowRecord | `(tenant, idempotency_key) WHERE != ''` | Idempotent escrow operations |
| Dispute | `(tenant, idempotency_key) WHERE != ''` | Idempotent dispute opening |
| RoleAssignment | `(tenant, user, role, scope_type, scope_id) WHERE is_active=True` | One active assignment per scope |
| CaregiverSkill | `(caregiver, name)` | No duplicate skill name per caregiver (DB backstop; service layer also checks case-insensitively) |
| CaregiverExperience | `CHECK(end_date IS NULL OR end_date >= start_date)` | End date cannot precede start date |

## Caregiver Dashboard Read Paths (Sprint 2.5 — no schema change)

Sprint 2.5 added zero models and zero migrations — it only added read selectors over
existing FK relationships that had no supplier-scoped query path before:

- `Order.assigned_supplier` → `apps.orders.services.queries.OrderQueryService
  .list_for_supplier()`/`count_by_status_for_supplier()` (new; mirrors the existing
  `list_for_customer()` shape, scoped by `assigned_supplier` instead of `customer_profile`).
- `FinancialDocument.beneficiary_party` → `apps.finance.services.document_service
  .FinancialDocumentService.list_for_beneficiary_party()`/`count_by_status_for_beneficiary_party()`
  (new; mirrors the existing `list_for_payer_party()` shape — the same `FinancialDocument`
  row, its other existing party column).
- `Review.supplier` → `apps.reviews.services.reputation_service.ReputationService
  .list_recent_reviews_with_reviewer_names()` (new; resolves `Review.reviewer_person_id` to
  `kernel.Person.full_name`, the same resolution `apps.public_site` already does for the
  public profile).

## Sprint 2.6 (Public Profile Finalization) — No Schema Change

Sprint 2.6 added zero models, zero fields, zero migrations — every change was a template
(SEO/accessibility/redundant-badge fix), test, or documentation change. No new FK
relationship, no new query path over an existing relationship. `VerificationDocument
.reviewed_by` (the internal document-moderation reviewer FK) was re-confirmed, by direct
inspection of `PublicCredentialSelector`/`PublicCredentialSummary`, to never be resolved or
exposed on any public surface — distinct from `Review.reviewer_person_id` above, which
*is* intentionally resolved to a public reviewer display name (a customer's own product
review, not credential-moderation data).

## Sprint 3.1 (Company Foundation and Caregiver Management) — Two Migrations

`OrganizationMembership` gained, across Sprint 3.1's original migration and the PR #12
architecture-review remediation's follow-up migration: `terminated_at` (DateTimeField,
nullable), `terminated_by` (FK to UserAccount, SET_NULL, `related_name="+"`),
`termination_reason` (CharField, blank), and `closure_reason` (CharField, blank,
choices=`AffiliationClosureReason`). No new model, no new FK relationship type — the
existing `organization`/`user`/`person`/`invited_by`/`approved_by` FKs are unchanged.
`CompanyAffiliationRequest` gained no new field; its existing `AffiliationStatus.CANCELLED`
value (already present, previously unused by any service function) is now reachable via
`cancel_affiliation_request()`.

**PR #12 architecture-review remediation (Blocker 1):** `OrganizationMembership`'s
`unique_together = [("organization", "user", "role_type")]` was removed and replaced with
two conditional `Meta.constraints` (`UniqueConstraint(condition=Q(...))`):
`uniq_active_caregiver_membership_per_user` (at most one ACTIVE caregiver-role membership
per user, globally) and `uniq_open_membership_per_org_user_role` (at most one open —
PENDING or ACTIVE — membership per organization+user+role_type). Terminal (REMOVED) rows
are excluded from both constraints, so they can coexist without limit. As a direct
consequence, a caregiver who leaves an organization and later rejoins the *same* one now
gets a **second, independent row** — `approve_affiliation_request()`/`invite_caregiver()`
always `.create()` a new row, never `update_or_create()` to reactivate a prior one. Every
affiliation period's `terminated_at`/`terminated_by`/`termination_reason`/`closure_reason`
is preserved unchanged on its own terminal row, directly queryable from the table itself —
`AuditLog` is a supplementary audit trail, not the source of affiliation-period history.
`CompanyAffiliationRequest` gained a matching conditional constraint,
`uniq_pending_affiliation_request_per_caregiver` (at most one PENDING request per
caregiver), closing the same race for join-by-code duplicate submissions. See
`traceability/ARCHITECTURE_DECISION_LOG.md` ADM-023's remediation note.

**Sprint 3.1 (including the PR #12 remediation) is now MERGED to `main`** (merge commit
`ffb82a4767ba115dc158cb845b92211ccbc30d00`); the schema described above is on `main`.

## Sprint 3.2 (Company Professional Profile and Public Presence) — One Migration

`OrganizationProfile` gained one new field: `headline` (CharField, max_length=150, blank).
No new model, no new FK relationship type. Wired through
`OrganizationProfileUpdateService.update_profile()`'s existing field whitelist (not a
generic mass-assignment path), both the organization-portal and public-site ViewModels, and
`common.bulk_supplier_attrs()`'s generic getattr-based attrs dict (the same pattern `city`/
`description` already use there).

No other schema change this sprint — the remaining Sprint 3.2 work (canonical
public-visibility-policy fix, SEO fix, media permission-gating, transaction-safe media
replacement) is entirely behavioral/service-layer, touching no field or FK.

## Append-Only Immutability

The following models are append-only (never updated after creation):
- PaymentTransaction, WalletTransaction, LedgerEntry, EscrowMovement
- AuditLog, EventOutbox, PaymentCallback
- ReleaseInstruction, RefundInstruction, CommissionSnapshot
- ObjectionPeriodExtension, PaymentDeadlineExtension
- DisputeResolution, FinancialDocumentItem, NotificationDeliveryAttempt
