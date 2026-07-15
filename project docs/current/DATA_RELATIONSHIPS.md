# DATA OWNERSHIP AND RELATIONSHIPS

**Last verified HEAD:** phase2-caregiver-professional-profile-foundation (from main @ 0c9d70c)
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

### CaregiverProfile → Related Entities (Phase 2.1 additions in bold)
```
CaregiverProfile
├── user → AUTH_USER_MODEL (CASCADE, OneToOne)
├── person → kernel.Person (CASCADE, OneToOne)
├── documents → accounts.VerificationDocument (CASCADE, reverse FK, related_name="documents")
├── **skills → accounts.CaregiverSkill (CASCADE, reverse FK, related_name="skills")**
└── **experiences → accounts.CaregiverExperience (CASCADE, reverse FK, related_name="experiences")**

CaregiverSkill (Phase 2.1, new)
├── caregiver → accounts.CaregiverProfile (CASCADE)
└── UNIQUE(caregiver, name)

CaregiverExperience (Phase 2.1, new)
├── caregiver → accounts.CaregiverProfile (CASCADE)
└── CHECK(end_date IS NULL OR end_date >= start_date)
```
Neither new model carries its own `tenant_id` — tenant is derived transitively via
`caregiver.user.tenant`, the same pattern `VerificationDocument` already uses for its own
caregiver/organization FKs (no `TenantAwareModel` base for any of the three).

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
