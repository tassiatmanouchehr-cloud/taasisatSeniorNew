# CURRENT SYSTEM FORENSIC ANALYSIS

## 1. Executive Summary

**Repository:** `tassiatmanouchehr-cloud/taasisatSenior`
**Current commit:** `a5dbaf28703142edaa1d770ea8f3c2a45a12640f` (PR #45 — Escrow & Disputes)
**Branch:** `main`
**Python:** 3.12.10
**Django:** 5.2.15
**Database:** PostgreSQL 16 (local install on port 5432)
**Test results:** 1632 tests passed, 0 failures (PostgreSQL)
**E2E workflow:** 18/18 steps passed

This is a modular monolith Django platform implementing an enterprise senior-care service marketplace. The system coordinates identity, matching, booking, execution, pricing, payment, escrow, commission, disputes, reviews, and reporting across a multi-tenant architecture.

---

## 2. Repository Structure

```
taasisatSenior/
├── src/                          # Django project root
│   ├── config/                   # Settings, URLs, WSGI, Celery
│   │   ├── settings/             # base.py, testing.py, development.py, production.py
│   │   ├── urls.py               # Root URL configuration
│   │   ├── celery.py             # Celery app configuration
│   │   └── wsgi.py
│   ├── apps/                     # 25 Django apps
│   │   ├── kernel/               # Tenant, Person, UserAccount, RBAC, ServiceSupplier, Config, Events, Audit
│   │   ├── accounts/             # Profiles, OTP, Registration, Documents, Media
│   │   ├── orders/               # ServiceCategory, ServiceType, Order, Eligibility, ShareLinks
│   │   ├── matching/             # MatchRound, MatchCandidate
│   │   ├── booking/              # SupplierAssignment
│   │   ├── execution/            # ExecutionSession
│   │   ├── finance/              # FinancialParty, FinancialDocument, Obligation, Ledger, Escrow, Settlement
│   │   ├── wallet/               # Wallet, WalletTransaction
│   │   ├── payments/             # PaymentIntent, PaymentAttempt, PaymentCallback, Settlement
│   │   ├── commission/           # CommissionContract, Deadline, ObjectionPeriod, Dispute, Refund, Snapshot
│   │   ├── notifications/        # Notification, DeliveryAttempt, Provider Registry
│   │   ├── availability/         # ProviderWorkingWindow, BlockedPeriod, CapacityRule
│   │   ├── pricing/              # PricingRule, Promotion, Quote
│   │   ├── discovery/            # Read-only supplier search/ranking (no models)
│   │   ├── reviews/              # Review, ReviewRating, ReputationSnapshot
│   │   ├── reporting/            # Read-only aggregation (no models)
│   │   ├── jobs/                 # JobDefinition, JobRun, handler registry
│   │   ├── api/                  # DRF API surface (/api/v1/)
│   │   ├── admin_portal/         # Server-rendered admin dashboards
│   │   ├── portal/               # Server-rendered customer portal
│   │   ├── provider_portal/      # Server-rendered provider portal
│   │   ├── organization_portal/  # Server-rendered organization admin portal
│   │   ├── public_site/          # Public marketing + discovery pages
│   │   ├── showcase/             # UI component library
│   │   └── common/               # Abstract base models, managers
│   ├── templates/                # Shared Django templates
│   ├── static/                   # Static assets
│   ├── ui/                       # Tailwind CSS, component partials
│   ├── locale/                   # i18n (empty placeholder)
│   ├── requirements/             # base.txt, test.txt, dev.txt
│   └── manage.py
├── module/                       # 25 Blueprint module spec packages (pre-code)
├── docs/                         # Architecture docs, ADRs
├── build_architecture_records/   # ADR-001
└── README.md
```

---

## 3. Django Apps Inventory

| App | INSTALLED_APPS Name | Purpose | Models | Services | Views | APIs |
|-----|-------------------|---------|--------|----------|-------|------|
| kernel | apps.kernel | Platform foundation: Tenant, Person, UserAccount, RBAC, ServiceSupplier, Config, Events, Audit | 14 | 10 | 1 (health) | 1 |
| accounts | apps.accounts | Profiles, OTP, Registration, Documents, Media | 10 | 10 | 9 | 0 |
| orders | apps.orders | Service catalog, Order lifecycle, Eligibility, ShareLinks | 6 | 5 | 0 | 0 |
| matching | apps.matching | MatchRound, MatchCandidate, Eligibility, Ranking | 2 | 3 | 0 | 0 |
| booking | apps.booking | SupplierAssignment | 1 | 4 | 0 | 0 |
| execution | apps.execution | ExecutionSession | 1 | 3 | 0 | 0 |
| finance | apps.finance | FinancialParty, Document, Item, Obligation, Ledger, Escrow, Settlement | 9 | 7 | 0 | 0 |
| wallet | apps.wallet | Wallet, WalletTransaction | 2 | 2 | 0 | 0 |
| payments | apps.payments | PaymentIntent, PaymentAttempt, PaymentCallback, Settlement | 3 | 4 | 0 | 3 |
| commission | apps.commission | CommissionContract, Deadline, ObjectionPeriod, Dispute, Refund, Snapshot | 8 | 11 | 0 | 0 |
| notifications | apps.notifications | Notification, DeliveryAttempt, Providers | 2 | 2 | 0 | 0 |
| availability | apps.availability | WorkingWindow, BlockedPeriod, CapacityRule | 3 | 3 | 0 | 0 |
| pricing | apps.pricing | PricingRule, Promotion, Quote | 4 | 3 | 0 | 1 |
| discovery | apps.discovery | Read-only search/ranking (no models) | 0 | 3 | 0 | 1 |
| reviews | apps.reviews | Review, ReviewRating, ReputationSnapshot | 3 | 3 | 0 | 2 |
| reporting | apps.reporting | Read-only aggregation (no models) | 0 | 5 | 0 | 2 |
| jobs | apps.jobs | JobDefinition, JobRun, handler registry | 2 | 1 | 0 | 0 |
| api | apps.api | DRF API surface | 0 | 0 | 12 | 12 |
| admin_portal | apps.admin_portal | Server-rendered admin dashboards | 0 | 0 | 13 | 0 |
| portal | apps.portal | Server-rendered customer portal | 0 | 0 | 30+ | 0 |
| provider_portal | apps.provider_portal | Server-rendered provider portal | 0 | 0 | 22 | 0 |
| organization_portal | apps.organization_portal | Server-rendered org admin portal | 0 | 0 | 18 | 0 |
| public_site | apps.public_site | Public marketing + discovery pages | 0 | 5 | 18 | 0 |
| showcase | apps.showcase | UI component library | 0 | 0 | 14 | 0 |
| common | apps.common | Abstract base models, managers | 0 | 0 | 0 | 0 |

**Totals:** 65 models, 78+ service classes, 150+ views, 12 API endpoints

---

## 4. Models Inventory

### 4.1 kernel (14 models)

| Model | Purpose | Key Fields |
|-------|---------|------------|
| Tenant | Multi-tenant root entity | id (UUID), name, slug (unique), status, settings (JSON), metadata (JSON), version |
| Person | Human identity (non-authenticating) | id (UUID), tenant (FK→Tenant), full_name, status, metadata, version |
| UserAccount | Django auth user (extends AbstractBaseUser) | id (UUID), person (FK→Person), tenant (FK→Tenant), email (unique), phone, is_active, is_staff |
| Role | RBAC role definition | id (UUID), tenant (FK→Tenant), name, slug, permissions (JSON list), is_system, version |
| Permission | Platform-global permission registry (dormant) | id (UUID), key (unique), module_id, resource_type, action, default_roles (JSON) |
| RoleAssignment | User-to-role binding with scope | id (UUID), tenant, user (FK→UserAccount), role (FK→Role), scope_type, scope_id, is_active, expires_at |
| EventOutbox | Persisted CES event envelope | id (UUID), tenant_id, event_type, payload (JSON), status, retry_count, max_retries |
| AuditLog | Append-only audit trail | id (UUID), tenant_id, actor_id, action, resource_type, before/after (JSON), audit_class |
| ConfigurationKey | CCS key definition | id (UUID), key (unique), owner_module, scope_level, value_type, default_value |
| ConfigurationValue | CCS scoped override | id (UUID), tenant_id, config_key (FK), scope_type, scope_id, value (JSON), is_active |
| FeatureFlag | Feature toggle per tenant | id (UUID), tenant_id, key, is_enabled, flag_type, percentage, kill_switch, targeting_rules (JSON) |
| PolicyDefinition | Versioned policy container | id (UUID), tenant_id, policy_type, name, owner_module, status, current_version_number |
| PolicyVersion | Specific policy version | id (UUID), tenant_id, policy (FK), version_number, rule_payload (JSON), effective_from, status |
| ServiceSupplier | Universal supply-side abstraction | id (UUID), tenant (FK), supplier_type, linked_entity_id/type, status, capabilities (JSON), verification_level, reputation_score |

### 4.2 accounts (10 models)

| Model | Purpose |
|-------|---------|
| OTPChallenge | Phone OTP verification (LOGIN/REGISTER) |
| VerificationDocument | Provider/org document uploads (9 types, PENDING/VERIFIED/REJECTED) |
| CustomerProfile | Customer identity (OneToOne to User, OneToOne to Person) |
| ElderProfile | Care recipient (FK→CustomerProfile) with care needs, mobility, allergies, etc. |
| TrustedContact | Emergency contact (FK→CustomerProfile) with access levels |
| CaregiverProfile | Provider identity (OneToOne to User, OneToOne to Person) with skills, bio, avatar |
| OrganizationProfile | Company identity (FK→User admin, FK→Tenant) with logo, registration |
| OrganizationMembership | Staff binding (FK→Org, FK→User) with role_type, status |
| CompanyAffiliationRequest | Caregiver→Org affiliation request |
| PlatformTeamMember | Platform staff (OneToOne to User) with team_area |

### 4.3 orders (6 models)

| Model | Purpose |
|-------|---------|
| ServiceCategory | Service catalog category (tenant-scoped) |
| ServiceType | Service catalog type (FK→Category, tenant-scoped) |
| Order | Root aggregate for service request (status machine, 7 states) |
| OrderOrganizationEligibility | Org→Order eligibility grant (sole-writer enforced) |
| OrderStatusHistory | Immutable audit of status transitions |
| OrderShareLink | Time-limited, revocable share token |

### 4.4 matching (2 models)

| Model | Purpose |
|-------|---------|
| MatchRound | Matching execution cycle (FK→Order) |
| MatchCandidate | Supplier candidate with eligibility, ranking, score |

### 4.5 booking (1 model)

| Model | Purpose |
|-------|---------|
| SupplierAssignment | Supplier commit to order (7 statuses, sequence-based, superseded_by self-FK) |

### 4.6 execution (1 model)

| Model | Purpose |
|-------|---------|
| ExecutionSession | On-the-ground delivery lifecycle (7 statuses, sequence-based) |

### 4.7 finance (9 models)

| Model | Purpose |
|-------|---------|
| FinancialParty | Universal financial counterparty |
| FinancialDocument | Invoice/credit/debit note (immutability enforced) |
| FinancialDocumentItem | Line items for financial documents |
| FinancialObligation | Pending financial duty |
| LedgerEntry | Immutable debit/credit record |
| PaymentTransaction | Internal payment record |
| EscrowRecord | Fund hold/release record |
| EscrowMovement | Immutable escrow conservation audit trail |
| SettlementBatch | Grouped payout batch |
| SettlementItem | Individual payout within batch |

### 4.8 wallet (2 models)

| Model | Purpose |
|-------|---------|
| Wallet | Stored-value account (party+currency unique) |
| WalletTransaction | Append-only ledger (overdraft support, idempotency) |

### 4.9 payments (3 models)

| Model | Purpose |
|-------|---------|
| PaymentIntent | Gateway-facing payment request |
| PaymentAttempt | Individual provider attempt |
| PaymentCallback | Inbound webhook record |

### 4.10 commission (8 models)

| Model | Purpose |
|-------|---------|
| CommissionContract | Company↔Caregiver commission agreement |
| CommissionSnapshot | Frozen commission state at assignment time |
| PaymentDeadline | Customer payment deadline with expiry |
| ObjectionPeriod | Post-service customer objection window |
| Dispute | Financial dispute (5 statuses) |
| DisputeLine | Individual disputed line item |
| DisputeResolution | Admin resolution with allocation |
| ReleaseInstruction | Escrow release instruction |
| RefundInstruction | Escrow refund instruction with PSP integration |

### 4.11 Other models

| App | Models |
|-----|--------|
| notifications | Notification, NotificationDeliveryAttempt |
| availability | ProviderWorkingWindow, AvailabilityBlockedPeriod, CapacityRule |
| pricing | PricingRule, Promotion, PromotionCondition, PromotionEffect, Quote |
| reviews | Review, ReviewRating, ReputationSnapshot |
| jobs | JobDefinition, JobRun |

---

## 5. Services Inventory

### 5.1 Kernel Services (10)

| Service | Purpose | Key Methods |
|---------|---------|-------------|
| AuditService | Central append-only audit | log(), log_security(), log_financial(), log_compliance() |
| EventPublisher | CES event emission | publish(), publish_batch() |
| ConfigResolver | CCS scope-hierarchy resolution | get(), get_or_default(), invalidate() |
| FeatureFlagService | Feature toggle evaluation | is_enabled(), invalidate() |
| PermissionService | Central RBAC enforcement | check(), require() |
| PolicyService | Versioned policy lifecycle | create_policy(), activate_version(), get_active_version() |
| RBACConfiguration | RBAC config wrapper | get_enforcement_enabled() |
| SupplierRegistry | ServiceSupplier CRUD | get_or_create_supplier(), resolve_by_id(), set_supplier_type() |
| SupplierResolver | Marketplace-model-aware resolution | resolve(), get_active_suppliers(), is_supplier_type_allowed() |
| TenantService | Default tenant resolution | get_default_tenant(), get_tenant_by_slug() |

### 5.2 Accounts Services (10)

| Service | Purpose |
|---------|---------|
| RegistrationService | Customer/Caregiver/Company registration |
| OTPService | OTP generate/verify with rate limiting |
| CareRecipientService | ElderProfile CRUD with ownership scoping |
| CaregiverProfileUpdateService | Caregiver self-edit (field-whitelisted) |
| OrganizationProfileUpdateService | Org self-edit with RBAC |
| OrganizationStaffService | Membership approve/suspend with row-locking |
| OrganizationRoleSyncService | Membership→RoleAssignment sync |
| DocumentService | Provider/org document upload with ownership |
| ProfileMediaService | Avatar/cover/logo management |
| supplier_bridge | Profile↔ServiceSupplier translation layer |

### 5.3 Orders Services (5)

| Service | Purpose |
|---------|---------|
| order_creation | create_public_order(), create_operator_order() |
| status_machine | 8 state transitions with select_for_update |
| eligibility_service | Organization eligibility grant/revoke |
| queries | Tenant/customer-scoped reads |
| share_links | Time-limited share token CRUD |

### 5.4 Matching Services (3)

| Service | Purpose |
|---------|---------|
| MatchOrchestrator | Run matching pass over an order |
| EligibilityService | Pure eligibility evaluation |
| RankingService | Deterministic weighted ranking |

### 5.5 Booking Services (4)

| Service | Purpose |
|---------|---------|
| AssignmentService | Supplier assignment (the ONLY mutator of Order.assigned_supplier) |
| OrganizationAssignmentService | Org admin manual assignment |
| ProviderAssignmentActionService | Provider confirm/decline |
| queries | Supplier-scoped reads |

### 5.6 Execution Services (3)

| Service | Purpose |
|---------|---------|
| ExecutionService | Session lifecycle (create/start/complete/close) |
| ProviderExecutionService | Ownership-gated start/complete |
| queries | Supplier-scoped reads |

### 5.7 Finance Services (7)

| Service | Purpose |
|---------|---------|
| FinancialDocumentService | Invoice creation/issue/lock/cancel |
| FinancialPartyService | FinancialParty resolution |
| EscrowService | Hold/release/refund with conservation tracking |
| LedgerService | Balanced ledger entry posting |
| PaymentService | Internal payment recording |
| ObligationService | Obligation creation from documents |
| SettlementService | Net position calculation, batch creation |

### 5.8 Wallet Services (2)

| Service | Purpose |
|---------|---------|
| WalletService | Wallet CRUD, balance calculation |
| WalletTransactionService | Credit/debit/refund with idempotency |

### 5.9 Payments Services (4)

| Service | Purpose |
|---------|---------|
| PaymentIntentService | Intent creation, attempt start |
| PaymentCallbackService | Provider callback processing |
| SettlementOrchestrationService | SUCCEEDED intent → money flow |
| provider_registry | Adapter registry (FAKE only) |

### 5.10 Commission Services (11)

| Service | Purpose |
|---------|---------|
| CommissionPolicyService | 3-tier policy management |
| CommissionContractService | Contract lifecycle (propose/approve/reject/terminate) |
| PaymentDeadlineService | Deadline creation/extension/expiry with cascade |
| AllocationCalculator | Commission split calculation (conservation-tested) |
| CommissionSnapshotService | Frozen commission state at assignment |
| ObjectionPeriodService | Post-service objection window |
| DisputeService | Dispute creation/resolution with allocation |
| RefundService | Refund instruction with PSP integration |
| EscrowIntegrationService | Pre-service payment → escrow hold bridge |
| CancellationEscrowService | Full refund on cancellation |
| ExecutionPaymentGuardService | Pre-service payment enforcement |

### 5.11 Other Services

| App | Services |
|-----|----------|
| notifications | NotificationDispatchService, NotificationQueryService |
| availability | AvailabilityQueryService, AvailabilityMutationService, CapacityService |
| pricing | QuoteService, PricingRuleService, PromotionService |
| discovery | DiscoveryService, SupplierSearchService, DiscoveryRankingService |
| reviews | ReviewSubmissionService, ReviewModerationService, ReputationService |
| reporting | ReportingService, OperationalReportService, ProviderReportService, FinancialReportService, MarketplaceReportService |
| jobs | JobService |
| public_site | CaregiverDirectoryService, CaregiverPublicProfileService, OrganizationPublicProfileService, HomePageService, common helpers |

---

## 6. API Inventory

### 6.1 DRF API Endpoints (12)

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | /api/v1/health/ | DB/cache health check | None |
| GET | /api/v1/discovery/suppliers/ | Supplier discovery search | RBAC: discovery.suppliers.read |
| POST | /api/v1/pricing/quotes/ | Generate price quote | RBAC: pricing.quotes.create |
| POST | /api/v1/reviews/ | Submit review | RBAC: reviews.submit |
| GET | /api/v1/suppliers/<uuid>/reputation/ | Supplier reputation summary | RBAC: reviews.read |
| GET | /api/v1/wallet/balance/ | Wallet balance | RBAC: wallet.read |
| GET | /api/v1/wallet/transactions/ | Wallet transactions | RBAC: wallet.read |
| POST | /api/v1/payments/intents/ | Create payment intent | RBAC: payments.intents.create |
| POST | /api/v1/payments/intents/<uuid>/attempts/ | Start payment attempt | RBAC: payments.attempts.create |
| POST | /api/v1/payments/callbacks/fake/ | Fake PSP callback | None (simulates webhook) |
| GET | /api/v1/sample/order-counts/ | Order count report | RBAC: reporting.read |
| GET | /api/v1/sample/providers/ | Provider reports | RBAC: reporting.read |

### 6.2 Template-Based Views (120+)

| Portal | Views | Purpose |
|--------|-------|---------|
| accounts | 9 | Login, register (3 types), verify, logout |
| admin_portal | 13 | Dashboards, financial oversight, disputes, escrow, system status |
| portal | 30+ | Dashboard, profile, care recipients, orders, financial, wizard (7-step), share links, notifications |
| provider_portal | 22 | Dashboard, assignments, visit start/complete, availability, earnings, profile, documents |
| organization_portal | 18 | Dashboard, staff management, assignment center, capacity, financial, reports, profile |
| public_site | 18 | Home, directory, caregiver/org profiles, static marketing pages |
| showcase | 14 | UI component browser |

---

## 7. Workflow Reconstruction

### 7.1 Order Lifecycle (State Machine)

```
PENDING_OPERATOR_REVIEW → NEW → WAITING_SERVICE → IN_PROGRESS → COMPLETED
                                        ↓                ↓
                               CANCELLATION_REQUESTED → CANCELLED
```

**Transitions:** approve_public_order, assign_supplier, remove_supplier, replace_supplier, start_order, complete_order, request_cancellation, approve_cancellation

### 7.2 Supplier Assignment Lifecycle

```
PROPOSED → ASSIGNED → CONFIRMED
    ↓          ↓
 DECLINED  REPLACED/CANCELLED/EXPIRED
```

### 7.3 Execution Session Lifecycle

```
SCHEDULED → IN_PROGRESS → PROVIDER_COMPLETED → CUSTOMER_PENDING → CLOSED
    ↓            ↓
 PAUSED     INTERRUPTED
```

### 7.4 Payment Flow

```
PaymentIntent (CREATED) → PaymentAttempt (INITIATED) → FakeCallback (SUCCEEDED)
    → SettlementOrchestrationService
        → FinancialDocumentService (resolve document)
        → PaymentService (record payment)
        → LedgerService (post balanced entries)
        → WalletTransactionService (credit beneficiary)
```

### 7.5 Escrow Flow (PR-B)

```
PaymentIntent (PRESERVICE) → EscrowService.hold_for_order()
    → ExecutionSession starts → service completes
    → ObjectionPeriodService.open()
        → Customer approves → EscrowService.apply_release()
        → Customer disputes → EscrowService.block_for_dispute()
        → Auto-approved → EscrowService.apply_release()
```

### 7.6 Commission Flow

```
AssignmentService.assign() → CommissionSnapshotService.create_snapshot_for_order()
    → PaymentDeadlineService.create_for_order()
    → (on payment) AllocationCalculator.calculate_shares()
    → SettlementOrchestrationService.settle_payment_intent()
```

### 7.7 Dispute Flow

```
Customer opens dispute → DisputeService.open()
    → Admin reviews → DisputeService.resolve() or DisputeService.reject()
    → If resolved → RefundService.initiate() → PSP adapter
```

---

## 8. State Machines

### 8.1 Order Status

| State | Transitions To |
|-------|---------------|
| PENDING_OPERATOR_REVIEW | NEW (approve), CANCELLED |
| NEW | WAITING_SERVICE (assign) |
| WAITING_SERVICE | IN_PROGRESS (start), CANCELLATION_REQUESTED |
| IN_PROGRESS | COMPLETED (complete), CANCELLATION_REQUESTED |
| CANCELLATION_REQUESTED | CANCELLED (approve) |
| COMPLETED | (terminal) |
| CANCELLED | (terminal) |

### 8.2 SupplierAssignment Status

| State | Transitions To |
|-------|---------------|
| PROPOSED | ASSIGNED, DECLINED, EXPIRED |
| ASSIGNED | CONFIRMED, DECLINED, REPLACED, CANCELLED, EXPIRED |
| CONFIRMED | (active) |
| DECLINED | (terminal) |
| REPLACED | (terminal) |
| CANCELLED | (terminal) |
| EXPIRED | (terminal) |

### 8.3 ExecutionSession Status

| State | Transitions To |
|-------|---------------|
| SCHEDULED | IN_PROGRESS, INTERRUPTED |
| IN_PROGRESS | PROVIDER_COMPLETED, PAUSED, INTERRUPTED |
| PROVIDER_COMPLETED | CLOSED, CUSTOMER_PENDING |
| CUSTOMER_PENDING | CLOSED |
| PAUSED | IN_PROGRESS |
| CLOSED | (terminal) |
| INTERRUPTED | (terminal) |

### 8.4 PaymentIntent Status

| State | Transitions To |
|-------|---------------|
| CREATED | INITIATED |
| INITIATED | SUCCEEDED, FAILED, EXPIRED |
| SUCCEEDED | (terminal) |
| FAILED | (terminal) |
| EXPIRED | (terminal) |

### 8.5 FinancialDocument Status

| State | Transitions To |
|-------|---------------|
| DRAFT | ISSUED, CANCELLED |
| ISSUED | LOCKED, PAID, PARTIALLY_PAID, DISPUTED |
| LOCKED | PAID, PARTIALLY_PAID |
| PAID | (terminal) |
| CANCELLED | (terminal) |

### 8.6 EscrowRecord Status (PR-B)

| State | Transitions To |
|-------|---------------|
| HELD | RELEASED, REFUNDED, BLOCKED |
| BLOCKED | RELEASED (dispute resolved) |
| RELEASED | (terminal) |
| REFUNDED | (terminal) |

### 8.7 Dispute Status

| State | Transitions To |
|-------|---------------|
| OPEN | UNDER_REVIEW, DISMISSED |
| UNDER_REVIEW | RESOLVED, DISMISSED |
| RESOLVED | (terminal) |
| DISMISSED | (terminal) |

---

## 9. Financial System Analysis

### 9.1 Payment Architecture

- **PaymentIntent**: Gateway-facing abstraction. States: CREATED→INITIATED→SUCCEEDED/FAILED/EXPIRED
- **PaymentAttempt**: Per-provider attempt within an intent. Row-locked for concurrency.
- **PaymentCallback**: Inbound webhook record. Fake adapter simulates PSP.
- **SettlementOrchestrationService**: Bridges SUCCEEDED intent to money flow. Posts balanced ledger entries, credits beneficiary wallet.

### 9.2 Escrow System (PR-B)

- **EscrowRecord**: Holds funds with conservation tracking (original = released + refunded + blocked + remaining)
- **EscrowMovement**: Immutable audit trail for every escrow state change
- **ObjectionPeriod**: Time window after service completion for customer to approve or dispute
- **ReleaseInstruction/RefundInstruction**: Admin-triggered escrow disposition

### 9.3 Commission System

- **CommissionContract**: Company↔Caregiver agreement with 3-way split (platform, company, caregiver)
- **CommissionSnapshot**: Frozen commission state at order assignment time
- **AllocationCalculator**: Deterministic split calculation (conservation-tested: platform + company + caregiver = 100%)
- **PaymentDeadline**: Customer payment deadline with auto-expiry cascade

### 9.4 Ledger

- **LedgerEntry**: Immutable, append-only. Every posting must balance (debit == credit). Single currency per group.
- **UniqueConstraint**: payment_transaction + account_code (idempotency backstop)

### 9.5 Wallet

- **Wallet**: Party+currency unique. Supports overdraft.
- **WalletTransaction**: Append-only. Types: CREDIT, DEBIT, REFUND, PROMOTION, MANUAL_ADJUSTMENT
- **Idempotency**: Per (wallet, idempotency_key) via IntegrityError catch

---

## 10. Permission Model

### 10.1 RBAC Architecture

- **Single evaluator**: `PermissionService.check()` and `.require()` are the ONLY code allowed to evaluate authorization
- **Fail-closed**: No matching RoleAssignment = deny
- **Organization-scoped**: RoleAssignment.scope_type="organization" + scope_id for org-specific permissions
- **Ownership fallback**: For callers without RBAC roles yet (audited, not silent)

### 10.2 Permission Keys (31 total)

| Domain | Keys |
|--------|------|
| booking | booking.assignment.assign (org-scoped) |
| commission | commission.policy.manage, commission.contract.propose (org-scoped), commission.contract.approve, commission.contract.terminate, commission.deadline.extend, commission.objection.extend, commission.dispute.resolve, commission.refund.authorize, commission.escrow.view |
| finance | finance.ledger.post, finance.payment.record, finance.settlement.create_batch, finance.document.issue, finance.document.lock |
| execution | execution.session.close |
| organization | organization.membership.approve (org-scoped), organization.membership.suspend (org-scoped), organization.profile.update (org-scoped) |
| reporting | reporting.read |
| discovery | discovery.suppliers.read |
| pricing | pricing.quotes.create |
| reviews | reviews.submit, reviews.read |
| wallet | wallet.read |
| payments | payments.intents.create, payments.attempts.create |
| admin | admin.portal.access, admin.tenants.read, admin.suppliers.read, admin.orders.read, admin.finance.read, admin.system.read |

### 10.3 Portal Authorization

Each portal uses ownership-based security:
- **Customer portal**: `resolve_customer_profile(request)` → user's own profile
- **Provider portal**: `resolve_supplier(request)` → user's own ServiceSupplier
- **Organization portal**: `resolve_organization(request)` → first administered organization
- **Admin portal**: `require_admin_permission(request, key)` → RBAC check

---

## 11. Database Structure

### 11.1 Entity Relationships

```
Tenant ─┬─ Person ── UserAccount ─┬─ CustomerProfile ── ElderProfile
        │                         │                     TrustedContact
        │                         ├─ CaregiverProfile
        │                         ├─ OrganizationMembership
        │                         └─ PlatformTeamMember
        ├─ Role ── RoleAssignment
        ├─ ServiceSupplier ─┬─ linked to CaregiverProfile
        │                   ├─ linked to OrganizationProfile
        │                   └─ linked to OrganizationMembership (via provider)
        ├─ Order ─┬─ OrderStatusHistory
        │         ├─ OrderShareLink
        │         ├─ OrderOrganizationEligibility
        │         ├─ SupplierAssignment ── MatchCandidate
        │         └─ ExecutionSession
        ├─ FinancialParty ─┬─ FinancialDocument ── FinancialDocumentItem
        │                  ├─ FinancialObligation
        │                  ├─ LedgerEntry
        │                  └─ PaymentTransaction
        ├─ Wallet ── WalletTransaction
        ├─ PaymentIntent ── PaymentAttempt ── PaymentCallback
        ├─ EscrowRecord ── EscrowMovement
        ├─ CommissionContract
        ├─ CommissionSnapshot
        ├─ PaymentDeadline
        ├─ ObjectionPeriod
        ├─ Dispute ── DisputeLine ── DisputeResolution
        ├─ ReleaseInstruction
        └─ RefundInstruction
```

### 11.2 Key Constraints

| Table | Constraint |
|-------|-----------|
| role_assignment | UniqueConstraint(tenant, user, role, scope_type, scope_id) WHERE is_active=True |
| order | UniqueConstraint(order_number) |
| supplier_assignment | UniqueConstraint(order, assignment_sequence) |
| execution_session | UniqueConstraint(order, execution_sequence) |
| wallet | UniqueConstraint(party_id, party_type, currency) |
| wallet_transaction | UniqueConstraint(wallet, idempotency_key) |
| ledger_entry | UniqueConstraint(payment_transaction, account_code) |
| service_supplier | Index(tenant, supplier_type, status), Index(tenant, status, availability_status) |
| financial_document | Index(tenant, document_type, status), Index(tenant, execution_session) |
| event_outbox | Index(status, created_at), Index(status, next_retry_at), Index(tenant_id, event_type, created_at) |
| audit_log | Index(tenant_id, occurred_at), Index(actor_id, occurred_at), Index(resource_type, resource_id) |

---

## 12. Dependency Analysis

### 12.1 Module Dependency Graph

```
kernel ← ALL apps
accounts ← orders, matching, booking, execution, finance, wallet, payments, commission, reviews, discovery, portal, provider_portal, organization_portal, public_site
orders ← matching, booking, execution, finance, commission, portal, admin_portal, provider_portal, organization_portal
matching ← booking
booking ← execution, commission
execution ← commission
finance ← payments, commission, wallet
wallet ← payments
payments ← commission
commission ← (self-contained after finance/wallet)
notifications ← (consumed by kernel event handlers)
availability ← matching, booking, discovery, provider_portal, organization_portal
pricing ← portal, api
discovery ← portal, public_site, api
reviews ← portal, public_site, api
reporting ← admin_portal, organization_portal, provider_portal, api
jobs ← payments (settlement.retry), notifications (dispatch_pending)
```

### 12.2 Cross-App Dependencies (Enforced)

- **No business module imports apps.api** (guardrail-tested)
- **No business module imports another business module's internal services** (convention)
- **apps.wallet is the canonical wallet** (apps.finance wallet is legacy/frozen, guardrail-tested)
- **EventOutbox touched only by EventPublisher and kernel.tasks** (guardrail-tested)
- **OrderOrganizationEligibility written only by eligibility_service** (guardrail-tested)

### 12.3 Circular Dependencies

**None detected.** Dependencies flow one-way through the service layer.

---

## 13. Test Analysis

### 13.1 Test Results

```
Total tests: 1632
Passed: 1632
Failed: 0
Duration: 320.6 seconds
Database: PostgreSQL 16 (test_marketplace)
```

### 13.2 Test Distribution by App

| App | Test Files | Notable Coverage |
|-----|-----------|-----------------|
| kernel | 21 | Architecture guardrails (12 tests), RBAC, permissions, config, events, policies |
| accounts | 12 | Registration, OTP, profiles, affiliations, documents, media, supplier bridge |
| orders | 4 | Order creation, status machine, eligibility, share links |
| matching | 6 | Eligibility, ranking, orchestrator |
| booking | 14 | Assignment, concurrency (2 tests), provider actions, organization assignment |
| execution | 10 | Session lifecycle, provider actions, payment guard |
| finance | 17 | Documents, party, ledger, escrow (conservation tests), settlement, obligation |
| wallet | 6 | Wallet service, transactions, atomicity (concurrency tests), tenant isolation |
| payments | 7 | Intent, callback, settlement orchestration (concurrency test), transitions |
| commission | 12 | Allocation calculator (conservation tests), contracts (concurrency), deadlines, disputes, refund |
| notifications | 4 | Dispatch, queries, providers |
| availability | 4 | Working windows, blocked periods, capacity |
| pricing | 7 | Quotes, rules, promotions |
| discovery | 6 | Search, ranking, filters |
| reviews | 6 | Submission, moderation, reputation, ownership, tenant isolation |
| reporting | 7 | Operational, financial, marketplace, provider reports |
| api | 14 | Pagination, permissions, all endpoints |
| admin_portal | 5 | Views, dispute resolution |
| portal | 15 | Dashboard, care recipients, requests, wizard, share links, financial |
| provider_portal | 14 | Dashboard, assignments, availability, profile, earnings |
| organization_portal | 8 | Dashboard, staff, assignment center, capacity |
| public_site | 20 | Directory, home, profiles, views, frontend remediation |
| jobs | 2 | Job service, handlers |

### 13.3 Architecture Guardrails (12 tests)

| Test | What It Enforces |
|------|-----------------|
| ApiViewOrmDisciplineTest | No ORM calls in API views |
| AdminPortalOrmDisciplineTest | No ORM calls in admin portal views |
| PortalOrmDisciplineTest | No ORM calls in customer portal views |
| ProviderPortalOrmDisciplineTest | No ORM calls in provider portal views |
| OrganizationPortalOrmDisciplineTest | No ORM calls in organization portal views |
| PublicSiteOrmDisciplineTest | No ORM calls in public site views |
| EventSystemSeparationTest | DomainEvent and EventOutbox are separate |
| NoDuplicateWalletModelTest | Only documented files define wallet models |
| NoReverseApiImportTest | Nothing imports apps.api except apps.api |
| OrderOrganizationEligibilitySoleWriterTest | No writes outside eligibility_service |
| ServiceSupplierProfileCouplingTest | No new direct profile imports outside allowlist |

### 13.4 Concurrency Tests (6 tests)

| Test | What It Verifies |
|------|-----------------|
| ConcurrentAssignmentTest | Exactly one concurrent assign succeeds |
| ConcurrentReplaceTest | Concurrent replaces don't corrupt sequence |
| WalletAtomicityTest.test_concurrent_movements_serialize_via_select_for_update | Concurrent debits serialize correctly |
| SettlementConcurrencyTest | Concurrent settlement attempts don't duplicate financial effects |
| ConcurrentProposeTest | Exactly one concurrent commission propose succeeds |
| ConcurrentApproveRejectTest | Exactly one concurrent approve/reject wins |

---

## 14. Duplicate Implementations

### 14.1 Wallet (Legacy vs Canonical)

| Aspect | apps.finance Wallet | apps.wallet |
|--------|-------------------|-------------|
| Models | WalletAccount, WalletTransaction | Wallet, WalletTransaction |
| Status | LEGACY/FROZEN (ADR-004) | CANONICAL |
| Tests | Own tests pass | Own tests pass |
| Guardrail | NoDuplicateWalletModelTest prevents third wallet | — |
| Runtime usage | None outside own tests | All production callers |

### 14.2 Role Catalogs

| Aspect | DEV_BOOTSTRAP_ROLES | DEFAULT_TENANT_ROLES |
|--------|--------------------|--------------------|
| Slug style | Hyphenated (organization-owner) | Underscored (organization_admin) |
| Tenant | dev | salmandyar |
| Permissions | Empty for most roles | Populated |
| Status | Intentionally distinct, not merged |

### 14.3 Permission Registry vs DB

| Aspect | apps.kernel.permissions (Python) | kernel.Permission (DB) |
|--------|--------------------------------|----------------------|
| Status | ACTIVE — source of truth | DORMANT — never read at runtime |
| Keys | 31 registered | Migrated but unused |
| Enforcement | Guardrail-tested | No-op |

---

## 15. Legacy Candidates

| Item | Location | Status |
|------|----------|--------|
| Finance Wallet | apps.finance.models.wallet | LEGACY/FROZEN (ADR-004). Guardrail-protected. No runtime usage. |
| kernel.Permission model | apps.kernel.models.rbac | DORMANT. Migrated but never read by PermissionService. |
| EventOutbox consumer dispatch | kernel.tasks._dispatch_to_consumers | No-op. Outbox infra complete, no real subscribers. |
| Celery Beat scheduler | config.settings.celery | Configured but no real tasks registered. |

---

## 16. Dead Code Candidates

| Item | Location | Evidence |
|------|----------|----------|
| list_unassigned_for_tenant() | apps.orders.services.queries | Exists but no callers (superseded by list_eligible_for_organization) |
| seed_product_walkthrough management command | apps.kernel.management.commands | DEBUG-gated, local dev only |
| showcase app | apps.showcase | Development-only UI component browser |
| Unused GIS_ENABLED flag | config.settings.base | Conditional PostGIS support, never enabled in tests |

---

## 17. Configuration Analysis

### 17.1 Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| SECRET_KEY | dev-only-insecure | Django secret key |
| DEBUG | False | Debug mode |
| DATABASE_ENGINE | django.db.backends.postgresql | DB backend |
| DATABASE_NAME | marketplace | DB name |
| DATABASE_USER | marketplace | DB user |
| DATABASE_PASSWORD | marketplace | DB password |
| DATABASE_HOST | localhost | DB host |
| DATABASE_PORT | 5432 | DB port |
| GIS_ENABLED | false | PostGIS support |
| REDIS_URL | (empty) | Redis cache |
| LANGUAGE_CODE | fa-ir | Persian locale |
| TIME_ZONE | Asia/Tehran | Iran timezone |

### 17.2 CCS Configuration Keys (120+)

Key domains: request, matching, booking, execution, financial, trust, communication, identity, search, geo, incentive, notification, document, review, CMS, workflow, analytics, API, config, AI, subscription, job, observability, i18n, marketplace.

### 17.3 Feature Flags

FeatureFlag model supports: BOOLEAN, PERCENTAGE, ACTOR_LIST, RULE_BASED modes with kill-switch, allowlist/blocklist, and targeting rules. No feature currently gates on a flag.

---

## 18. External Integrations

| Integration | Status | Implementation |
|-------------|--------|---------------|
| Payment Provider | FAKE | FakePaymentProviderAdapter (simulates PSP webhook) |
| SMS | FAKE | FakeSmsProvider (logs to console) |
| Email | FAKE | FakeEmailProvider (logs to console) |
| Push Notification | FAKE | FakePushProvider (logs to console) |
| In-App Notification | FAKE | FakeInAppProvider (logs to console) |
| File/Object Storage | LOCAL | Django's default FileSystemStorage |
| Geocoding | NOT_IMPLEMENTED | No lat/long, no geocoding anywhere |
| OpenAPI Schema | CONFIGURED_BUT_UNUSED | drf-spectacular installed, not wired |
| Redis | OPTIONAL | Falls back to LocMemCache if not configured |
| Celery | OPTIONAL | Configured but no real tasks |

---

## 19. Infrastructure Overview

### 19.1 Docker

- Dockerfile.dev: Python 3.12-slim with GDAL, PostGIS, build tools
- entrypoint.sh: Database wait + migrate + collectstatic
- No docker-compose.yml (local PostgreSQL used)

### 19.2 CI/CD

- `.github/workflows/ci.yml`: 5 jobs (lint, ui-quality, tailwind, test, visual-regression)
- **Never actually executed** (GitHub Actions not enabled for this repo)
- Lint: ruff check + ruff format
- Test: PostgreSQL 16 + PostGIS + Redis 7
- Visual: Playwright accessibility/visual-snapshot tests

### 19.3 Frontend Stack

- Django Templates + HTMX + Alpine.js + Tailwind CSS 3.x
- Persian RTL-first (lang="fa-IR", dir="rtl")
- Jalali/Shamsi dates (jdatetime)
- Design tokens via Tailwind config
- Tailwind build: ui/css/main.css → static/css/output.css

---

## 20. Current System Capability Matrix

| Capability | Status | Readiness |
|-----------|--------|-----------|
| Multi-tenancy | IMPLEMENTED | L4 |
| Identity/Auth | IMPLEMENTED | L3 |
| Customer Registration | IMPLEMENTED | L4 |
| Caregiver Registration | IMPLEMENTED | L4 |
| Organization Registration | IMPLEMENTED | L3 |
| Elder/Care Recipient | IMPLEMENTED | L4 |
| Trusted Contacts | IMPLEMENTED | L3 |
| Service Catalog | IMPLEMENTED | L4 |
| Order Creation | IMPLEMENTED | L4 |
| Order Lifecycle | IMPLEMENTED | L4 |
| Matching | PARTIALLY_IMPLEMENTED | L2 |
| Booking/Assignment | IMPLEMENTED | L4 |
| Provider Accept/Decline | IMPLEMENTED | L4 |
| Execution Start/Complete | IMPLEMENTED | L4 |
| Pricing/Quotes | IMPLEMENTED | L3 |
| Payment Intent | IMPLEMENTED | L3 |
| Fake Payment | IMPLEMENTED | L3 |
| Settlement | IMPLEMENTED | L3 |
| Wallet | IMPLEMENTED | L4 |
| Ledger | IMPLEMENTED | L4 |
| Escrow (PR-B) | IMPLEMENTED | L3 |
| Commission | IMPLEMENTED | L3 |
| Disputes (PR-B) | IMPLEMENTED | L3 |
| Objection Period | IMPLEMENTED | L3 |
| Refunds | IMPLEMENTED | L3 |
| Reviews | IMPLEMENTED | L4 |
| Reputation | IMPLEMENTED | L4 |
| Notifications | PARTIALLY_IMPLEMENTED | L2 |
| Background Jobs | IMPLEMENTED | L3 |
| Event Outbox | PARTIALLY_IMPLEMENTED | L2 |
| Audit Logging | IMPLEMENTED | L4 |
| RBAC | IMPLEMENTED | L4 |
| Configuration | IMPLEMENTED | L3 |
| Feature Flags | PARTIALLY_IMPLEMENTED | L2 |
| Reporting | IMPLEMENTED | L3 |
| Public Discovery | IMPLEMENTED | L4 |
| Customer Portal | IMPLEMENTED | L4 |
| Provider Portal | IMPLEMENTED | L4 |
| Organization Portal | IMPLEMENTED | L4 |
| Admin Portal | IMPLEMENTED | L3 |
| DRF API | IMPLEMENTED | L3 |
| Geospatial | NOT_IMPLEMENTED | L0 |
| Document/Media Storage | PARTIALLY_IMPLEMENTED | L2 |
| CMS/Content | NOT_IMPLEMENTED | L0 |
| Workflow Automation | NOT_IMPLEMENTED | L0 |
| AI/Recommendations | NOT_IMPLEMENTED | L0 |
| Subscriptions | NOT_IMPLEMENTED | L0 |
| Real PSP Integration | NOT_IMPLEMENTED | L0 |
| Real SMS/Email | NOT_IMPLEMENTED | L0 |
| Real Geocoding | NOT_IMPLEMENTED | L0 |
| OpenAPI Schema | CONFIGURED_BUT_UNUSED | L1 |
| CI/CD Pipeline | IMPLEMENTED_BUT_UNVERIFIED | L2 |
| Production Deployment | NOT_IMPLEMENTED | L0 |
