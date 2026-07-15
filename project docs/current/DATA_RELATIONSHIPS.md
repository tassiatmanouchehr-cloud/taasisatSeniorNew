# DATA OWNERSHIP AND RELATIONSHIPS

**Last verified HEAD:** phase2-caregiver-availability-schedule (from main @ 20c532e, PR #8 merged)
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

## Append-Only Immutability

The following models are append-only (never updated after creation):
- PaymentTransaction, WalletTransaction, LedgerEntry, EscrowMovement
- AuditLog, EventOutbox, PaymentCallback
- ReleaseInstruction, RefundInstruction, CommissionSnapshot
- ObjectionPeriodExtension, PaymentDeadlineExtension
- DisputeResolution, FinancialDocumentItem, NotificationDeliveryAttempt
