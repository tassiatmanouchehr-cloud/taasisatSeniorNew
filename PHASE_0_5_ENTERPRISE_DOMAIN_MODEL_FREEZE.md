# Phase 0.5 — Enterprise Domain Model Freeze

## Enterprise Service Marketplace Platform

**Date:** July 6, 2026
**Phase:** 0.5 (between Phase 0 and Phase 1)
**Status:** Pending Owner Approval
**Purpose:** Freeze the complete enterprise domain model before any production code is written
**Rule:** No Django models, no migrations, no database tables, no serializers, no APIs, no production code until this document is approved.

---

## Table of Contents

1. [Enterprise Domain Model](#deliverable-1)
2. [Person / Identity Model](#deliverable-2)
3. [Organization Structure](#deliverable-3)
4. [Branch Architecture](#deliverable-4)
5. [Service Catalog Engine](#deliverable-5)
6. [Capability Engine](#deliverable-6)
7. [Availability Engine](#deliverable-7)
8. [Pricing Engine](#deliverable-8)
9. [Resource & Equipment Model](#deliverable-9)
10. [Marketplace Visibility Rules](#deliverable-10)
11. [Aggregate Boundaries](#deliverable-11)
12. [Entity Lifecycle Diagrams](#deliverable-12)
13. [Cardinality Matrix](#deliverable-13)
14. [Cross-Module Entity Ownership](#deliverable-14)
15. [PostgreSQL Schema Layout](#deliverable-15)
16. [Shared Kernel Entity Catalog](#deliverable-16)
17. [Migration Strategy](#deliverable-17)
18. [Architecture Validation](#deliverable-18)

---


<a id="deliverable-1"></a>
## Deliverable 1 — Enterprise Domain Model

### Complete Entity Catalog

Every entity below is categorized by its owning module/domain, with ownership and lifecycle noted.

---

### 1.1 Platform Kernel (Module 25 / Shared Kernel)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **Platform** | Kernel | Singleton | The marketplace platform instance itself |
| **Tenant** | Kernel | create → active → suspended → archived | Isolated business tenant |
| **Person** | Kernel | create → active → deactivated | Natural person identity (never duplicated) |
| **UserAccount** | Kernel | create → active → locked → deactivated | Authentication account bound to a Person |
| **Identity** | Kernel | unverified → basic → advanced → premium | Verification level of a Person |
| **Credential** | Kernel | active → rotated → revoked | Login credential (password, OTP, OAuth) |
| **Role** | Kernel | draft → active → deprecated | Named permission bundle |
| **Permission** | Kernel | registered → active → deprecated | Granular operation permission |
| **RoleAssignment** | Kernel | granted → active → expired → revoked | Binds Person+Role within a scope |
| **FeatureFlag** | Kernel | draft → enabled → disabled → archived | Feature toggle with targeting |
| **ConfigurationKey** | Kernel | registered → active → deprecated | CCS configuration definition |
| **ConfigurationValue** | Kernel | active → superseded → archived | Scoped configuration override |
| **PolicyDefinition** | Kernel | draft → active → deprecated → archived | Versioned policy container |
| **PolicyVersion** | Kernel | draft → active → superseded (immutable) | Specific policy snapshot |
| **ServiceSupplier** | Kernel | pending → active → suspended → deactivated | Universal supply-side abstraction |
| **AuditLog** | Kernel | created (immutable, append-only) | Audit trail entry |
| **EventOutbox** | Kernel | pending → published → dead_letter | CES event outbox record |
| **CorrelationContext** | Kernel | transient (request-scoped) | Request tracing context |

### 1.2 Identity & Organizations (Module 08)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **Organization** | M08 | pending → approved → active → suspended → dissolved | Provider-side business entity |
| **Branch** | M08 | draft → active → suspended → closed | Physical/logical location within an org |
| **Department** | M08 | active → archived | Functional unit within an org/branch |
| **Team** | M08 | active → archived | Working group within a department |
| **OrganizationMembership** | M08 | invited → active → suspended → terminated | Person-to-org relationship |
| **BranchAssignment** | M08 | active → transferred → ended | Person assigned to a specific branch |
| **IndependentProviderProfile** | M08 | draft → pending_verification → active → suspended | Provider working independently |
| **OrganizationProviderProfile** | M08 | draft → pending_approval → active → suspended | Provider affiliated with an org |
| **CustomerProfile** | M08 | draft → active → suspended | Customer-side profile |
| **CustomerDelegate** | M08 | invited → active → revoked | Person acting on behalf of a customer |
| **TrustedPerson** | M08 | granted → active → expired → revoked | Order-scoped temporary visibility |
| **VerificationRequest** | M08 | submitted → in_review → approved → rejected | Identity/document verification |
| **ProfileField** | M08 | active (versioned) | Individual profile attribute |

### 1.3 Service Catalog (Module 09 / New: Catalog Engine)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **ServiceCategory** | Catalog | draft → active → deprecated → archived | Top-level service classification |
| **Service** | Catalog | draft → active → suspended → archived | Specific service offering |
| **ServicePackage** | Catalog | draft → active → deprecated | Bundled service configuration |
| **ServiceOption** | Catalog | active → deprecated | Configurable option within a service |
| **ServiceVariant** | Catalog | active → deprecated | Variant (e.g., size, duration tier) |
| **ServiceAttribute** | Catalog | active → deprecated | Descriptive attribute (metadata) |
| **ServiceUnit** | Catalog | active | Unit of measurement (hour, session, visit) |
| **PricingTemplate** | Catalog | draft → active → superseded | Base pricing rules for a service |
| **RequiredCapability** | Catalog | active | Capability needed to deliver a service |
| **RequiredDocument** | Catalog | active | Document required for service delivery |
| **RequiredEquipment** | Catalog | active | Equipment needed for service delivery |
| **ExecutionRule** | Catalog | active → superseded | Rules governing service execution |

### 1.4 Capability & Skills (Cross-Module)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **Capability** | Catalog | active → deprecated | Verified ability (e.g., Electrical, ICU, Deep Cleaning) |
| **CapabilityCategory** | Catalog | active → deprecated | Grouping of capabilities |
| **Skill** | M08 | claimed → verified → expired | Provider's declared/verified skill |
| **Certification** | M08 | submitted → verified → active → expired | Formal certification record |
| **CapabilityAssignment** | Kernel | active → revoked | Links supplier to capabilities |

### 1.5 Availability & Scheduling (Module: Availability Engine)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **Schedule** | Availability | active → superseded | Weekly schedule template |
| **WorkingHours** | Availability | active | Day-of-week time slots |
| **Holiday** | Availability | scheduled → active → passed | Calendar holiday definition |
| **Leave** | Availability | requested → approved → active → completed | Time-off record |
| **TemporaryUnavailability** | Availability | active → expired | Short-term unavailability block |
| **AvailabilitySlot** | Availability | available → reserved → booked → released | Bookable time slot |
| **CapacityLimit** | Availability | active → superseded | Max daily/concurrent order limits |
| **EmergencyAvailability** | Availability | declared → active → expired | On-call/emergency availability |

### 1.6 Geospatial & Location (Module 10)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **Address** | M10 | created → validated → archived | Structured postal address |
| **GeoLocation** | M10 | created → validated | GPS coordinates with accuracy |
| **ServiceArea** | M10 | draft → active → suspended → archived | Geographic coverage boundary |
| **GeofenceRule** | M10 | active → disabled | Area-based trigger rule |
| **RouteEstimate** | M10 | calculated (transient/cached) | Distance/time calculation |
| **LiveLocationSession** | M10 | started → active → ended | Real-time tracking session |

### 1.7 Request & Order (Module 01, 03)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **ServiceRequest** | M01 | draft → submitted → approved → published → matched → closed | Service request from customer |
| **RequestServiceNeed** | M01 | draft → confirmed | Individual service requirement |
| **ServiceRecipient** | M01 | active | Person receiving the service |
| **ServiceCase** | M03 | created → active → completed → closed | Overarching case (multi-session) |
| **ServiceAssignment** | M03 | created → accepted → active → completed → cancelled | Supplier-to-case commercial assignment |
| **ExecutionAssignment** | M03 | pending → assigned → active → completed | Execution provider internal assignment |
| **ServiceSession** | M03 | scheduled → confirmed → ready → in_progress → completed | Individual session within a case |
| **AssignmentPlan** | M03 | draft → confirmed → active | Planned schedule for assignments |

### 1.8 Matching (Module 02)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **MatchRound** | M02 | started → completed → failed | Single matching execution |
| **MatchCandidate** | M02 | generated → ranked → presented → responded → selected/rejected | Candidate supplier |
| **CandidateResponse** | M02 | pending → accepted → declined → expired | Supplier response |
| **CustomerSelection** | M02 | made → confirmed → cancelled | Customer's choice |
| **EligibilityEvaluation** | M02 | evaluated (immutable) | Rule evaluation result |
| **RankingScore** | M02 | calculated (immutable) | Composite ranking score |

### 1.9 Service Execution (Module 04)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **ExecutionSession** | M04 | ready → en_route → arrived → started → in_progress → paused → completed → closed | Active session execution |
| **PresenceRecord** | M04 | created (immutable) | Location verification record |
| **StartChecklist** | M04 | pending → completed → failed | Pre-service checklist |
| **ExecutionActivity** | M04 | created → in_progress → completed → skipped | Task during service |
| **ObservationRecord** | M04 | recorded (immutable) | Provider observation |
| **EvidenceItem** | M04 | captured → submitted → accepted → rejected | Photo/doc/signature evidence |
| **Interaction** | M04 | sent → delivered → read | In-execution communication |
| **ExecutionException** | M04 | created → assigned → resolved → closed | Unexpected issue |
| **ExtensionRequest** | M04 | requested → approved → rejected → applied | Duration extension |
| **CompletionRecord** | M04 | pending_confirmation → confirmed → disputed | Service completion |
| **HandoverRecord** | M04 | created → acknowledged | Session-to-session handover |

### 1.10 Financial Operations (Module 05)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **FinancialParty** | M05 | created → active → suspended | Entity with financial identity |
| **CommercialContract** | M05 | drafted → active → completed → cancelled | Price/terms agreement |
| **FinancialDocument** | M05 | drafted → issued → paid → posted → closed | Invoice, credit/debit note |
| **PaymentTransaction** | M05 | initiated → processing → completed → failed | Payment attempt |
| **WalletAccount** | M05 | created → active → frozen → closed | Stored-value account |
| **EscrowAccount** | M05 | created → funded → allocated → released → closed | Held funds |
| **LedgerEntry** | M05 | posted (immutable, append-only) | Double-entry ledger record |
| **LedgerJournal** | M05 | posted (immutable) | Group of related ledger entries |
| **SettlementBatch** | M05 | created → processing → completed → failed | Grouped payouts |
| **SettlementItem** | M05 | scheduled → processing → completed → failed | Individual payout |
| **FinancialReservation** | M05 | created → released → expired | Payment hold |
| **Refund** | M05 | requested → approved → processed → rejected | Refund lifecycle |
| **Adjustment** | M05 | created → approved → posted | Manual financial correction |
| **FinancialObligation** | M05 | created → fulfilled → waived | Pending financial duty |

### 1.11 Pricing Engine (Cross-Module: M05 + Catalog)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **PricePolicy** | Pricing | draft → active → superseded | Versioned pricing rule set |
| **PriceComponent** | Pricing | active → deprecated | Individual price element (base, fee, surcharge) |
| **PriceCalculation** | Pricing | calculated (immutable) | Recorded price computation |
| **Discount** | Pricing | active → expired | Price reduction rule |
| **Coupon** | Pricing | created → active → redeemed → expired | Discount code |
| **TaxRule** | Pricing | active → superseded | Tax calculation rule |
| **InsuranceFee** | Pricing | active → superseded | Insurance surcharge rule |
| **CommissionPolicy** | Pricing | draft → active → superseded | Platform/org commission rates |
| **DynamicPricingRule** | Pricing | active → disabled | Demand-based price adjustment |

### 1.12 Trust & Governance (Module 06)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **TrustCase** | M06 | opened → investigating → decided → closed | Investigation case |
| **Review** | M06 | submitted → moderated → published → hidden | User review |
| **Rating** | M06 | submitted → published | Numerical rating |
| **ReputationProfile** | M06 | active (continuously updated) | Aggregate reputation |
| **Complaint** | M06 | submitted → acknowledged → investigating → resolved | Formal complaint |
| **Dispute** | M06 | opened → mediation → resolved → escalated | Service dispute |
| **EnforcementAction** | M06 | recommended → approved → applied → expired | Sanction |
| **Appeal** | M06 | submitted → reviewing → approved → rejected | Appeal of enforcement |
| **RiskSignal** | M06 | raised → assessed → dismissed → actioned | Risk indicator |

### 1.13 Communication (Module 07 + 12)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **CommunicationRule** | M07 | draft → active → disabled | Event-to-communication mapping |
| **CommunicationSession** | M07 | created → processing → completed → failed | Orchestration lifecycle |
| **CommunicationDeliveryJob** | M12 | queued → sending → delivered → failed → retrying | Delivery task |
| **CommunicationTemplate** | M07 | draft → active → deprecated | Versioned message template |
| **CommunicationPreference** | M07 | active | User channel/category preferences |
| **InboxItem** | M07 | created → read → archived | In-app message |
| **Conversation** | M07 | active → closed | Threaded conversation |
| **Notification** | M12 | sent → delivered → read → failed | Individual notification record |
| **Reminder** | M07 | scheduled → triggered → cancelled | Scheduled reminder |
| **Campaign** | M07 | draft → scheduled → running → completed | Bulk communication |

### 1.14 Incentives & Promotions (Module 11)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **IncentiveCampaign** | M11 | draft → active → paused → completed → archived | Marketing campaign |
| **Promotion** | M11 | draft → active → expired → archived | Promotion rule |
| **PromotionApplication** | M11 | applied → confirmed → reversed | Applied promotion instance |
| **ReferralRelationship** | M11 | created → converted → expired | Referrer-to-referee |
| **Reward** | M11 | earned → pending_payout → paid → cancelled | Earned reward |
| **CommissionAdjustment** | M11 | created → applied → reversed | Commission override |

### 1.15 Documents & Media (Module 13)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **Document** | M13 | uploaded → processing → ready → archived → deleted | File record |
| **DocumentVersion** | M13 | created → active → superseded | Version of a document |
| **MediaAsset** | M13 | uploaded → processed → active → archived | Image/video/audio |
| **DocumentRequirement** | M13 | required → submitted → verified → rejected | Required doc tracking |
| **Signature** | M13 | requested → signed → verified | Digital signature |

### 1.16 Resources & Equipment (Cross-Module)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **Resource** | Catalog | registered → active → maintenance → decommissioned | Physical resource |
| **ResourceType** | Catalog | active → deprecated | Category of resource |
| **ResourceAssignment** | Kernel | assigned → in_use → returned | Resource-to-supplier binding |
| **ResourceRequirement** | Catalog | active | Resource needed for a service |

### 1.17 Workflow & Automation (Module 16)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **WorkflowDefinition** | M16 | draft → active → deprecated | Workflow template |
| **WorkflowInstance** | M16 | started → running → completed → failed → cancelled | Running workflow |
| **WorkflowStep** | M16 | pending → running → completed → failed → skipped | Individual step |
| **WorkflowTimer** | M16 | scheduled → triggered → cancelled | Time-based trigger |

### 1.18 Background Jobs (Module 22)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **JobDefinition** | M22 | active → disabled | Job type definition |
| **JobExecution** | M22 | scheduled → queued → running → completed → failed → dead_letter | Job run |
| **JobSchedule** | M22 | active → paused → disabled | Cron/periodic schedule |

### 1.19 Analytics & Reporting (Module 17)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **MetricDefinition** | M17 | active → deprecated | KPI/metric definition |
| **Dashboard** | M17 | draft → published → archived | Analytics dashboard |
| **Report** | M17 | scheduled → generated → delivered | Scheduled report |
| **DataExport** | M17 | requested → processing → ready → expired | Data export job |

### 1.20 Integration (Module 18)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **IntegrationEndpoint** | M18 | configured → active → disabled | External API endpoint |
| **IntegrationCredential** | M18 | active → rotated → revoked | Stored credentials |
| **WebhookSubscription** | M18 | active → disabled | Webhook registration |
| **IntegrationLog** | M18 | recorded (immutable) | API call log |

### 1.21 AI & Recommendations (Module 20)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **AIModel** | M20 | training → deployed → active → deprecated | ML model record |
| **Recommendation** | M20 | generated → presented → accepted → rejected → expired | Recommendation |
| **Prediction** | M20 | generated → evaluated | Prediction record |
| **HumanOverride** | M20 | recorded (immutable) | Override of AI decision |

### 1.22 Search & Discovery (Module 09)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **SearchIndex** | M09 | building → active → rebuilding → stale | Search index definition |
| **SearchableDocument** | M09 | indexed → updated → removed | Indexed entity |
| **FacetDefinition** | M09 | active → deprecated | Configurable filter |
| **RankingProfile** | M09 | active → superseded | Ranking algorithm config |
| **SavedSearch** | M09 | active → archived | User's saved query |

### 1.23 Observability (Module 23)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **HealthCheck** | M23 | passing → degraded → failing | Service health status |
| **Alert** | M23 | triggered → acknowledged → resolved | Alert instance |
| **Incident** | M23 | opened → investigating → mitigated → resolved → closed | Operational incident |
| **SLODefinition** | M23 | active → deprecated | Service level objective |

### 1.24 Localization & Theme (Module 24 + Kernel)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **Locale** | M24 | active → deprecated | Supported locale |
| **TranslationEntry** | M24 | draft → published | Translation string |
| **CalendarSystem** | M24 | active | Supported calendar (Gregorian, Jalali) |
| **Theme** | Kernel | draft → active → deprecated | UI theme definition |
| **ThemeOverride** | Kernel | active → superseded | Tenant-specific theme |

### 1.25 Subscription & Licensing (Module 21)

| Entity | Owner | Lifecycle | Description |
|--------|-------|-----------|-------------|
| **Plan** | M21 | draft → active → deprecated → archived | Subscription plan |
| **Subscription** | M21 | trial → active → past_due → cancelled → expired | Active subscription |
| **Entitlement** | M21 | granted → active → expired → revoked | Feature/quota entitlement |
| **UsageRecord** | M21 | recorded (immutable) | Metered usage event |

---

**Total Entity Count: ~160 entities across all modules.**

---


<a id="deliverable-2"></a>
## Deliverable 2 — Person / Identity Model

### Core Principle

**A User ≠ A Provider.** A Person is a stable identity that can hold many roles simultaneously or over time without creating duplicate records.

### Identity Hierarchy

```
Person (stable, never duplicated)
  │
  ├── UserAccount (authentication — one or more per person)
  │     ├── Credential (password, OTP, OAuth, biometric)
  │     └── Session (active login sessions)
  │
  ├── Identity Verification (progressive levels)
  │     ├── unverified
  │     ├── basic (phone/email verified)
  │     ├── advanced (document verified)
  │     └── premium (in-person or notarized)
  │
  ├── Memberships (many, concurrent)
  │     ├── OrganizationMembership → Organization → Branch → Department
  │     ├── PlatformMembership (platform staff)
  │     └── Each membership carries:
  │           ├── Roles (many per membership)
  │           ├── Permissions (derived from roles)
  │           └── Scope (tenant, org, branch, department)
  │
  ├── Profiles (context-specific views)
  │     ├── CustomerProfile
  │     ├── IndependentProviderProfile
  │     ├── OrganizationProviderProfile
  │     └── PlatformStaffProfile
  │
  └── ServiceSupplier Records (linked from profiles)
        ├── INDEPENDENT_PROVIDER → IndependentProviderProfile
        ├── ORGANIZATION → Organization
        └── ORGANIZATION_PROVIDER → OrganizationProviderProfile
```

### Same Person — Multiple Roles (Supported Without Duplication)

| Scenario | How It Works |
|----------|-------------|
| Person is Customer AND Provider | One Person, two Profiles (CustomerProfile + IndependentProviderProfile), two ServiceSupplier records possible |
| Person is Organization Owner AND Customer | One Person, OrganizationMembership (role=owner) + CustomerProfile |
| Person is Platform Staff AND Customer | One Person, PlatformMembership + CustomerProfile |
| Person moves from Independent to Organization | IndependentProviderProfile deactivated, OrganizationProviderProfile created, ServiceSupplier updated |
| Person leaves Organization | OrganizationMembership terminated, OrganizationProviderProfile suspended, may reactivate IndependentProviderProfile |

### Key Rules

1. **Person.id is permanent** — never deleted, only deactivated
2. **UserAccount is for authentication** — a Person may have multiple accounts (e.g., phone + email)
3. **Profiles are for context** — they hold domain-specific data, not identity
4. **Memberships change** — roles and affiliations are temporal
5. **ServiceSupplier is the business interface** — other modules reference suppliers, not profiles
6. **Identity verification is independent** — it attaches to Person, not to a specific role
7. **Permissions are evaluated per-request** — using current memberships + roles + scope + context

### Entity Relationships

```
Person 1──* UserAccount
Person 1──1 IdentityVerification
Person 1──* OrganizationMembership
Person 1──0..1 CustomerProfile
Person 1──0..1 IndependentProviderProfile
Person 1──0..1 OrganizationProviderProfile
Person 1──0..1 PlatformStaffProfile
Person 1──* RoleAssignment (through memberships)
IndependentProviderProfile 1──1 ServiceSupplier (type=INDEPENDENT_PROVIDER)
OrganizationProviderProfile 1──1 ServiceSupplier (type=ORGANIZATION_PROVIDER)
Organization 1──1 ServiceSupplier (type=ORGANIZATION)
```

---

<a id="deliverable-3"></a>
## Deliverable 3 — Organization Structure

### Hierarchy

```
Organization
├── Branch (1..N physical/logical locations)
│   ├── Department (0..N functional units)
│   │   └── Team (0..N working groups)
│   └── Direct staff (not in departments)
├── Global staff (not branch-specific)
└── Organization-wide policies/settings
```

### Supported Organizational Roles (Not Hard-Coded)

| Role Category | Examples | Notes |
|---------------|----------|-------|
| Leadership | Owner, Director, CEO | Full org access |
| Operations | Operator, Dispatcher, Coordinator | Order management |
| Service Delivery | Provider, Technician, Nurse | Service execution |
| Finance | Accountant, Finance Manager | Financial operations |
| HR | HR Manager, Recruiter | Personnel management |
| Compliance | Compliance Officer, Auditor | Governance |
| IT | System Admin, IT Support | Technical operations |
| Marketing | Marketing Manager, Campaign Manager | Growth |
| Support | Customer Support, Help Desk | Issue handling |
| Custom | Any tenant-defined role | Configurable |

**Implementation:** Roles are data rows in `kernel_role` with `scope_type = 'organization'`, not hard-coded enums. Each organization/tenant can create custom roles.

### Organization Entity Model

```
Organization
├── id                      UUID
├── tenant_id               UUID → Tenant
├── name                    VARCHAR(255)
├── slug                    VARCHAR(100)
├── legal_name              VARCHAR(255)
├── registration_number     VARCHAR(100)
├── tax_id                  VARCHAR(100)
├── organization_type       VARCHAR(50)  # agency, clinic, company, studio, etc.
├── status                  ENUM(pending, approved, active, suspended, dissolved)
├── owner_person_id         UUID → Person
├── primary_address_id      UUID → Address
├── primary_contact         JSONB
├── settings                JSONB  # org-level configuration overrides
├── branding                JSONB  # logo, colors, display name
├── capabilities            JSONB  # org-level capabilities
├── financial_party_id      UUID → FinancialParty
├── supplier_id             UUID → ServiceSupplier
├── metadata                JSONB
├── created_at, updated_at, version
└── Module: M08
```

### Organization Does NOT Hard-Code

- ❌ Number of branches
- ❌ Department names
- ❌ Team structures
- ❌ Role names (beyond defaults)
- ❌ Working hours
- ❌ Service categories
- ❌ Commission rates
- ❌ Notification preferences

All of these are data-driven and configurable per organization per tenant.

---

<a id="deliverable-4"></a>
## Deliverable 4 — Branch Architecture

### Branch Entity Model

```
Branch
├── id                      UUID
├── tenant_id               UUID → Tenant
├── organization_id         UUID → Organization
├── name                    VARCHAR(255)
├── slug                    VARCHAR(100)
├── branch_type             VARCHAR(50)  # headquarters, satellite, virtual, mobile
├── status                  ENUM(draft, active, suspended, closed)
├── address_id              UUID → Address
├── geo_location_id         UUID → GeoLocation
├── service_area_ids        JSONB  # references to ServiceArea entities
├── contact_info            JSONB  # phone, email, etc.
├── working_hours_id        UUID → Schedule
├── timezone                VARCHAR(50)
├── financial_settings      JSONB  # branch-specific financial overrides
├── notification_policy     JSONB  # branch notification preferences
├── operator_team_ids       JSONB  # persons assigned as operators
├── max_providers           INTEGER NULL
├── capabilities            JSONB  # branch-level capabilities
├── settings                JSONB  # branch-specific config overrides
├── metadata                JSONB
├── created_at, updated_at, version
└── Module: M08
```

### Branch Capabilities (Each Branch May Have Its Own)

| Capability | Description |
|------------|-------------|
| Own address | Physical location independent from org headquarters |
| Own service area | Separate geographic coverage zone(s) |
| Own providers | Staff assigned specifically to this branch |
| Own schedules | Branch-specific working hours and calendar |
| Own holidays | Branch-local holidays (different from org or national) |
| Own financial settings | Payment methods, settlement schedules, bank details |
| Own operator team | Branch-specific dispatchers/coordinators |
| Own notifications | Branch-level notification routing |
| Own availability | Branch-specific capacity limits |
| Own service catalog subset | Branch may offer subset of org services |

### Branch Assignment Model

```
BranchAssignment
├── id                      UUID
├── tenant_id               UUID → Tenant
├── person_id               UUID → Person
├── branch_id               UUID → Branch
├── role_id                 UUID → Role
├── assignment_type         ENUM(primary, secondary, temporary, backup)
├── status                  ENUM(active, suspended, transferred, ended)
├── effective_from          TIMESTAMPTZ
├── effective_until         TIMESTAMPTZ NULL
├── metadata                JSONB
└── Module: M08
```

### Resolution Order for Branch-Aware Configuration

```
1. Branch-specific override
2. Organization-level override
3. Tenant-level default
4. Platform default
```

This ensures each branch can customize behavior without code changes.

---

<a id="deliverable-5"></a>
## Deliverable 5 — Service Catalog Engine

### Catalog Hierarchy

```
ServiceCategory (top-level classification)
├── ServiceCategory (nested, unlimited depth)
│   └── Service (concrete service offering)
│       ├── ServicePackage (bundled configuration)
│       │   └── PackageItem (service + options included)
│       ├── ServiceOption (configurable add-on)
│       │   └── OptionChoice (selectable value)
│       ├── ServiceVariant (size/tier/duration variant)
│       ├── ServiceAttribute (descriptive metadata)
│       ├── PricingTemplate (base pricing rules)
│       ├── RequiredCapability (what supplier needs)
│       ├── RequiredDocument (docs needed)
│       ├── RequiredEquipment (equipment needed)
│       ├── EstimatedDuration (time estimate)
│       └── ExecutionRule (how service is delivered)
└── ServiceUnit (measurement: hour, session, visit, piece)
```

### Key Entities

```
ServiceCategory
├── id, tenant_id, parent_id (self-referential for nesting)
├── name, slug, description
├── icon, image
├── display_order
├── status (draft, active, deprecated, archived)
├── is_leaf (can services attach here?)
├── metadata, settings
└── Module: Catalog

Service
├── id, tenant_id
├── category_id             UUID → ServiceCategory
├── name, slug, description
├── service_type            VARCHAR(50)  # one_time, recurring, subscription, on_demand
├── unit_id                 UUID → ServiceUnit
├── default_duration        INTERVAL
├── min_duration, max_duration
├── base_price_template_id  UUID → PricingTemplate
├── required_capabilities   JSONB  # list of capability IDs
├── required_documents      JSONB
├── required_equipment      JSONB
├── execution_rules         JSONB
├── matching_tags           JSONB  # tags for matching engine
├── is_bookable             BOOLEAN
├── requires_approval       BOOLEAN
├── status (draft, active, suspended, archived)
├── metadata
└── Module: Catalog

ServicePackage
├── id, tenant_id
├── service_id              UUID → Service
├── name, description
├── package_items           JSONB  # [{service_id, quantity, options}]
├── pricing_template_id     UUID → PricingTemplate
├── discount_percentage     DECIMAL
├── validity_days           INTEGER
├── status
└── Module: Catalog
```

### Catalog Rules

1. **One service may belong to exactly one leaf category** — but categories nest
2. **Categories are tenant-configurable** — different tenants may have different category trees
3. **Services are never industry-specific in code** — "nursing visit" and "plumbing repair" are both just `Service` rows
4. **Display labels come from localization** — category/service names are translatable
5. **Pricing is separate from catalog** — PricingTemplate is a reference, not embedded
6. **Capabilities drive matching** — services declare required capabilities; suppliers declare held capabilities

---

<a id="deliverable-6"></a>
## Deliverable 6 — Capability Engine

### Architecture

Capabilities are **independent from service categories**. A capability represents a verified ability; a category represents a classification. The same capability can be required by services in different categories.

```
CapabilityCategory (grouping)
├── Capability (specific ability)
│   ├── CapabilityLevel (optional: basic, intermediate, advanced, expert)
│   └── ValidationRules (how to verify this capability)
└── CapabilityAssignment (links to supplier/provider)
```

### Entity Models

```
CapabilityCategory
├── id, tenant_id
├── name, slug, description
├── parent_id (self-referential for nesting)
├── icon
├── status (active, deprecated)
└── Module: Catalog

Capability
├── id, tenant_id
├── category_id             UUID → CapabilityCategory
├── name, slug, description
├── capability_type         VARCHAR(50)  # skill, certification, equipment, license
├── has_levels              BOOLEAN
├── levels                  JSONB  # [{level: 'basic', requirements: [...]}, ...]
├── validation_method       VARCHAR(50)  # self_declared, document_verified, test_passed, peer_reviewed
├── expiry_policy           JSONB  # {expires: true, duration_months: 12, renewal_required: true}
├── is_mandatory_for_matching  BOOLEAN
├── status (active, deprecated)
├── metadata
└── Module: Catalog

CapabilityAssignment
├── id, tenant_id
├── supplier_id             UUID → ServiceSupplier
├── capability_id           UUID → Capability
├── level                   VARCHAR(50) NULL  # if capability has_levels
├── status                  ENUM(claimed, pending_verification, verified, expired, revoked)
├── verified_at             TIMESTAMPTZ NULL
├── verified_by             UUID NULL → Person
├── expires_at              TIMESTAMPTZ NULL
├── evidence_ids            JSONB  # references to verification documents
├── metadata
└── Module: Kernel (cross-module)
```

### Example Capability Trees (Data, Not Code)

```
Medical
├── ICU Care (levels: basic, advanced)
├── Injection (levels: intramuscular, intravenous)
├── Wound Care
├── Elder Care (levels: basic, specialized, dementia)
├── Pediatric Care
└── Physiotherapy

Electrical
├── Residential Wiring
├── Industrial Wiring
├── Smart Home Installation
├── Solar Panel Installation
└── Emergency Repair

Cleaning
├── Residential Cleaning
├── Deep Cleaning
├── Office Cleaning
├── Post-Construction Cleaning
└── Specialized (medical facility, cleanroom)
```

### Matching Integration

```
Matching Engine query:
  - Service requires: [Capability A (level: advanced), Capability B]
  - Supplier has: [Capability A (level: expert), Capability B, Capability C]
  - Result: ELIGIBLE (expert >= advanced for A; B matches)
```

Capabilities drive eligibility. Categories alone are insufficient because a "nursing" provider may not have ICU capability.

---


<a id="deliverable-7"></a>
## Deliverable 7 — Availability Engine

### Core Principle

Availability is an **independent subsystem** — never embedded inside Provider, Organization, or Branch models. It composes with any entity that has schedulable capacity.

### Architecture

```
AvailabilityOwner (polymorphic: Supplier, Branch, Organization)
├── Schedule (weekly template)
│   └── WorkingHours (per day-of-week time slots)
├── CalendarOverride (specific date overrides)
│   ├── Holiday (recurring or one-time)
│   ├── Leave (personal time-off)
│   └── TemporaryUnavailability (short-term block)
├── CapacityLimit (maximum load constraints)
│   ├── MaxDailyOrders
│   ├── MaxConcurrentOrders
│   └── MaxWeeklyHours
├── EmergencyAvailability (on-call declarations)
└── AvailabilitySlot (computed, bookable time windows)
```

### Entity Models

```
Schedule
├── id, tenant_id
├── owner_type              VARCHAR(50)  # 'supplier', 'branch', 'organization'
├── owner_id                UUID
├── name                    VARCHAR(255)
├── schedule_type           ENUM(regular, emergency, holiday, temporary)
├── effective_from          DATE
├── effective_until         DATE NULL
├── timezone                VARCHAR(50)
├── status                  ENUM(active, superseded, archived)
├── metadata                JSONB
└── Module: Availability

WorkingHours
├── id, tenant_id
├── schedule_id             UUID → Schedule
├── day_of_week             SMALLINT (0=Saturday for Jalali, configurable)
├── start_time              TIME
├── end_time                TIME
├── is_active               BOOLEAN
├── break_start             TIME NULL
├── break_end               TIME NULL
├── slot_duration_minutes   INTEGER (default booking slot size)
├── metadata                JSONB
└── Module: Availability

Holiday
├── id, tenant_id
├── name                    VARCHAR(255)
├── holiday_type            ENUM(national, religious, organizational, branch, custom)
├── date                    DATE NULL (for one-time)
├── recurrence_rule         JSONB NULL (for recurring: month/day, Jalali-aware)
├── calendar_system         VARCHAR(20) DEFAULT 'jalali'
├── applies_to_type         VARCHAR(50)  # 'platform', 'tenant', 'organization', 'branch'
├── applies_to_id           UUID NULL
├── affects_availability    BOOLEAN DEFAULT true
├── affects_pricing         BOOLEAN DEFAULT false (triggers holiday fee)
├── status                  ENUM(scheduled, active, passed)
└── Module: Availability

Leave
├── id, tenant_id
├── person_id               UUID → Person
├── supplier_id             UUID → ServiceSupplier NULL
├── leave_type              ENUM(vacation, sick, personal, maternity, emergency, other)
├── start_date              DATE
├── end_date                DATE
├── start_time              TIME NULL (partial day)
├── end_time                TIME NULL
├── status                  ENUM(requested, approved, active, completed, cancelled, rejected)
├── approved_by             UUID NULL → Person
├── reason                  TEXT
├── metadata                JSONB
└── Module: Availability

TemporaryUnavailability
├── id, tenant_id
├── owner_type              VARCHAR(50)
├── owner_id                UUID
├── reason                  VARCHAR(255)
├── start_at                TIMESTAMPTZ
├── end_at                  TIMESTAMPTZ
├── is_recurring            BOOLEAN DEFAULT false
├── recurrence_rule         JSONB NULL
├── status                  ENUM(active, expired, cancelled)
└── Module: Availability

CapacityLimit
├── id, tenant_id
├── owner_type              VARCHAR(50)
├── owner_id                UUID
├── limit_type              ENUM(max_daily_orders, max_concurrent_orders, max_weekly_hours, max_daily_hours, max_travel_radius)
├── limit_value             INTEGER
├── effective_from          DATE
├── effective_until         DATE NULL
├── status                  ENUM(active, superseded)
└── Module: Availability

EmergencyAvailability
├── id, tenant_id
├── supplier_id             UUID → ServiceSupplier
├── declaration_type        ENUM(on_call, standby, immediate)
├── start_at                TIMESTAMPTZ
├── end_at                  TIMESTAMPTZ
├── response_time_minutes   INTEGER
├── premium_rate_applies    BOOLEAN
├── status                  ENUM(declared, active, expired, cancelled)
└── Module: Availability

AvailabilitySlot (Computed/Materialized)
├── id, tenant_id
├── owner_type              VARCHAR(50)
├── owner_id                UUID
├── date                    DATE
├── start_time              TIME
├── end_time                TIME
├── slot_status             ENUM(available, reserved, booked, blocked, holiday, leave)
├── booking_ref_id          UUID NULL
├── computed_at             TIMESTAMPTZ
└── Module: Availability
```

### Resolution Order

When determining if a supplier is available at a given time:

```
1. Check TemporaryUnavailability (blocks)
2. Check Leave (blocks)
3. Check Holiday (blocks unless emergency)
4. Check Schedule + WorkingHours (must be within)
5. Check CapacityLimit (must not exceed)
6. Check EmergencyAvailability (overrides blocks for on-call)
```

### Branch/Organization Availability Inheritance

```
Platform Holiday → applies to all
  └── Tenant Holiday → applies to tenant
       └── Organization Holiday → applies to org
            └── Branch Holiday → applies to branch
                 └── Supplier Schedule → individual working hours
                      └── Leave/Temp blocks → personal overrides
```

---

<a id="deliverable-8"></a>
## Deliverable 8 — Pricing Engine

### Core Principle

Pricing is **independent from Financial Operations (Module 05)**. The Pricing Engine calculates prices; Module 05 handles payments, ledger, and settlement. They are separate concerns.

### Price Calculation Architecture

```
PriceCalculation = Σ PriceComponents

Components:
├── BasePrice (from PricingTemplate)
├── + TravelFee (distance-based)
├── + DistanceFee (per-km surcharge)
├── + NightFee (time-of-day surcharge)
├── + HolidayFee (holiday surcharge)
├── + UrgentFee (short-notice premium)
├── + WeekendFee (weekend surcharge)
├── + SpecialEquipmentFee
├── - Discount (rule-based reduction)
├── - Promotion (campaign discount)
├── - Coupon (code-based discount)
├── + Tax (rule-based tax)
├── + InsuranceFee (if applicable)
├── = GrossPrice
│
├── Platform Commission = GrossPrice × platform_rate
├── Organization Commission = GrossPrice × org_rate (if applicable)
├── Provider Share = GrossPrice - Platform Commission - Org Commission
└── = NetPayable
```

### Entity Models

```
PricePolicy
├── id, tenant_id
├── policy_type             ENUM(standard, dynamic, promotional, contract, custom)
├── name, description
├── applies_to_type         VARCHAR(50)  # 'service', 'category', 'supplier_type', 'tenant'
├── applies_to_id           UUID NULL
├── version                 INTEGER
├── status                  ENUM(draft, active, superseded, archived)
├── effective_from          TIMESTAMPTZ
├── effective_until         TIMESTAMPTZ NULL
├── priority                INTEGER (higher wins on conflict)
├── rules                   JSONB  # policy rule payload
├── metadata                JSONB
└── Module: Pricing

PriceComponent
├── id, tenant_id
├── policy_id               UUID → PricePolicy
├── component_type          ENUM(base, travel, distance, night, holiday, urgent, weekend, equipment, discount, promotion, coupon, tax, insurance, custom)
├── name                    VARCHAR(255)
├── calculation_method      ENUM(fixed, percentage, per_unit, per_km, tiered, formula)
├── value                   DECIMAL  # fixed amount or percentage
├── formula                 JSONB NULL  # for complex calculations
├── conditions              JSONB  # when this component applies
├── min_value               DECIMAL NULL
├── max_value               DECIMAL NULL
├── currency                VARCHAR(3) DEFAULT 'IRR'
├── is_taxable              BOOLEAN DEFAULT true
├── display_to_customer     BOOLEAN DEFAULT true
├── status                  ENUM(active, deprecated)
└── Module: Pricing

PriceCalculation (Immutable Record)
├── id, tenant_id
├── order_id                UUID NULL
├── service_id              UUID → Service
├── supplier_id             UUID → ServiceSupplier NULL
├── policy_id               UUID → PricePolicy
├── components_breakdown    JSONB  # [{type, name, value, calculation_detail}]
├── subtotal                DECIMAL
├── discount_total          DECIMAL
├── tax_total               DECIMAL
├── gross_total             DECIMAL
├── platform_commission     DECIMAL
├── organization_commission DECIMAL NULL
├── provider_share          DECIMAL
├── currency                VARCHAR(3)
├── calculated_at           TIMESTAMPTZ
├── valid_until             TIMESTAMPTZ NULL
├── metadata                JSONB
└── Module: Pricing

CommissionPolicy
├── id, tenant_id
├── commission_type         ENUM(platform, organization, referral, incentive)
├── target_type             VARCHAR(50)  # 'all', 'supplier_type', 'category', 'service'
├── target_id               UUID NULL
├── rate_type               ENUM(percentage, fixed, tiered)
├── rate_value              DECIMAL
├── tiers                   JSONB NULL  # [{min_amount, max_amount, rate}]
├── min_commission          DECIMAL NULL
├── max_commission          DECIMAL NULL
├── version                 INTEGER
├── status                  ENUM(draft, active, superseded)
├── effective_from          TIMESTAMPTZ
├── effective_until         TIMESTAMPTZ NULL
└── Module: Pricing

DynamicPricingRule
├── id, tenant_id
├── name, description
├── trigger_type            ENUM(demand, time_of_day, day_of_week, season, capacity, custom)
├── trigger_conditions      JSONB  # {demand_threshold: 0.8, time_range: "22:00-06:00", ...}
├── adjustment_type         ENUM(multiplier, fixed_surcharge, percentage_surcharge)
├── adjustment_value        DECIMAL
├── max_multiplier          DECIMAL  # ceiling
├── status                  ENUM(active, disabled)
├── effective_from          TIMESTAMPTZ
├── effective_until         TIMESTAMPTZ NULL
└── Module: Pricing

Coupon
├── id, tenant_id
├── code                    VARCHAR(50) UNIQUE per tenant
├── coupon_type             ENUM(percentage, fixed, free_delivery)
├── value                   DECIMAL
├── max_discount            DECIMAL NULL
├── min_order_value         DECIMAL NULL
├── usage_limit             INTEGER NULL (total uses)
├── per_user_limit          INTEGER DEFAULT 1
├── times_used              INTEGER DEFAULT 0
├── valid_from              TIMESTAMPTZ
├── valid_until             TIMESTAMPTZ
├── applies_to_services     JSONB NULL  # specific service IDs
├── applies_to_categories   JSONB NULL
├── status                  ENUM(active, exhausted, expired, disabled)
└── Module: Pricing
```

### Pricing vs. Financial Operations Boundary

| Concern | Pricing Engine | Financial Operations (M05) |
|---------|---------------|---------------------------|
| Calculate price | ✅ | ❌ |
| Apply discounts/promotions | ✅ | ❌ |
| Determine commission split | ✅ | ❌ |
| Issue invoice | ❌ | ✅ |
| Process payment | ❌ | ✅ |
| Post ledger entries | ❌ | ✅ |
| Execute settlement | ❌ | ✅ |
| Handle refunds | ❌ | ✅ |

---

<a id="deliverable-9"></a>
## Deliverable 9 — Resource & Equipment Model

### Architecture

Resources are physical or virtual assets that suppliers use to deliver services. They may be required for service eligibility and may participate in matching and scheduling.

```
ResourceType (classification)
└── Resource (specific asset)
    ├── ResourceAssignment (linked to supplier)
    └── ResourceRequirement (linked to service)
```

### Entity Models

```
ResourceType
├── id, tenant_id
├── name, slug, description
├── category               ENUM(vehicle, medical_equipment, cleaning_equipment, power_tools, specialized_device, technology, other)
├── attributes_schema      JSONB  # defines expected attributes for this type
├── maintenance_policy     JSONB  # maintenance schedule rules
├── status                 ENUM(active, deprecated)
└── Module: Catalog

Resource
├── id, tenant_id
├── resource_type_id       UUID → ResourceType
├── owner_type             VARCHAR(50)  # 'supplier', 'organization', 'branch', 'platform'
├── owner_id               UUID
├── name                   VARCHAR(255)
├── identifier             VARCHAR(100)  # license plate, serial number, etc.
├── attributes             JSONB  # type-specific attributes
├── status                 ENUM(registered, active, maintenance, unavailable, decommissioned)
├── condition              ENUM(excellent, good, fair, needs_repair)
├── location_id            UUID NULL → GeoLocation
├── last_maintenance_at    TIMESTAMPTZ NULL
├── next_maintenance_at    TIMESTAMPTZ NULL
├── metadata               JSONB
└── Module: Catalog

ResourceAssignment
├── id, tenant_id
├── resource_id            UUID → Resource
├── supplier_id            UUID → ServiceSupplier
├── assignment_type        ENUM(permanent, temporary, shared, per_order)
├── status                 ENUM(assigned, in_use, returned, released)
├── assigned_from          TIMESTAMPTZ
├── assigned_until         TIMESTAMPTZ NULL
├── order_id               UUID NULL (for per-order assignments)
└── Module: Kernel

ResourceRequirement
├── id, tenant_id
├── service_id             UUID → Service
├── resource_type_id       UUID → ResourceType
├── is_mandatory           BOOLEAN DEFAULT true
├── quantity               INTEGER DEFAULT 1
├── attributes_filter      JSONB NULL  # required attribute values
├── notes                  TEXT
└── Module: Catalog
```

### Examples

| Resource Type | Examples |
|---------------|----------|
| Vehicle | Car, motorcycle, van, truck, ambulance |
| Medical Equipment | Blood pressure monitor, glucometer, wheelchair, oxygen tank |
| Cleaning Equipment | Industrial vacuum, pressure washer, steam cleaner |
| Power Tools | Drill, welder, multimeter, cable tester |
| Specialized Devices | Diagnostic scanner, thermal camera, air quality meter |
| Technology | Tablet, POS terminal, portable printer |

### Matching Integration

When matching a service request to suppliers:
1. Check if service has `ResourceRequirement` entries
2. Query suppliers who have matching `Resource` (via `ResourceAssignment`) that is in `active` status
3. Exclude suppliers whose required resources are in `maintenance` or `unavailable`

---

<a id="deliverable-10"></a>
## Deliverable 10 — Marketplace Visibility Rules

### Core Principle

Visibility (which suppliers appear to customers) is **never hard-coded**. It is resolved through a configurable policy system combining marketplace model, visibility strategy, and ranking rules.

### Visibility Policy Architecture

```
VisibilityPolicy
├── MarketplaceModel (which supplier types are active)
├── VisibilityStrategy (how to select/order candidates)
├── RankingWeights (how to score candidates)
├── FilterRules (eligibility gates)
└── ExclusionRules (who to exclude)
```

### Supported Marketplace Models (Configuration)

| Model | Suppliers Shown | Config Key |
|-------|----------------|-----------|
| `independent_only` | Only independent providers | `marketplace.supplier_model` |
| `organization_only` | Only organizations | `marketplace.supplier_model` |
| `hybrid` | Both types | `marketplace.supplier_model` |

### Supported Visibility Strategies (Configuration)

| Strategy | Behavior | Use Case |
|----------|----------|----------|
| `organization_first` | Show orgs first, then independents | Trust organizations more |
| `independent_first` | Show independents first, then orgs | Promote individual providers |
| `round_robin` | Alternate fairly between types | Fairness |
| `nearest` | Sort by geographic proximity | Location-sensitive services |
| `highest_rated` | Sort by reputation score desc | Quality-first |
| `lowest_cost` | Sort by price asc | Price-sensitive customers |
| `best_match` | Composite score (capability + proximity + rating + availability) | General marketplace |
| `policy_score` | Custom policy-defined scoring | Enterprise customization |
| `ai_recommendation` | AI model-driven ranking | Intelligent matching |

### Entity Model

```
VisibilityPolicy
├── id, tenant_id
├── name, description
├── marketplace_model       ENUM(independent_only, organization_only, hybrid)
├── visibility_strategy     ENUM(organization_first, independent_first, round_robin, nearest, highest_rated, lowest_cost, best_match, policy_score, ai_recommendation)
├── ranking_weights         JSONB  # {proximity: 0.3, rating: 0.25, price: 0.2, capability_match: 0.15, availability: 0.1}
├── filter_rules            JSONB  # [{field, operator, value}]
├── exclusion_rules         JSONB  # [{condition, reason}]
├── max_results             INTEGER DEFAULT 20
├── include_unavailable     BOOLEAN DEFAULT false (show but mark as unavailable)
├── show_supplier_type      BOOLEAN DEFAULT true (display type badge)
├── allow_customer_filter   BOOLEAN DEFAULT true (let customer filter by type)
├── version                 INTEGER
├── status                  ENUM(draft, active, superseded)
├── effective_from          TIMESTAMPTZ
├── effective_until         TIMESTAMPTZ NULL
├── applies_to_category     UUID NULL → ServiceCategory
├── applies_to_region       UUID NULL → ServiceArea
└── Module: M02 (Matching) + M19 (Config)
```

### Resolution Example

```python
# Pseudocode — never hard-coded
def resolve_visibility(request, tenant_id):
    policy = VisibilityPolicyResolver.get_active(tenant_id, request.category, request.location)

    suppliers = SupplierResolver.get_active_suppliers(tenant_id)
    suppliers = apply_marketplace_model_filter(suppliers, policy.marketplace_model)
    suppliers = apply_filter_rules(suppliers, policy.filter_rules)
    suppliers = apply_exclusion_rules(suppliers, policy.exclusion_rules)
    suppliers = apply_availability_check(suppliers, request.datetime)
    suppliers = apply_capability_check(suppliers, request.required_capabilities)
    suppliers = rank_by_strategy(suppliers, policy.visibility_strategy, policy.ranking_weights)
    return suppliers[:policy.max_results]
```

---

<a id="deliverable-11"></a>
## Deliverable 11 — Aggregate Boundaries (DDD)

### Aggregate Definitions

Each aggregate defines a **consistency boundary** — all changes within an aggregate are transactional; cross-aggregate communication is eventually consistent (via CES events).

---

### Identity Aggregate (Module 08)

```
Root: Person
Contains: UserAccount, Credential, IdentityVerification, ProfileField
Boundary: One person's identity data
Transaction: Creating/updating a person's auth and verification
Events Emitted: Person.Created, User.Registered, Identity.Verified
```

### Organization Aggregate (Module 08)

```
Root: Organization
Contains: Branch, Department, Team, OrganizationMembership, BranchAssignment
Boundary: One organization's structural data
Transaction: Org creation, branch addition, membership changes
Events Emitted: Organization.Created, Branch.Added, Membership.Changed
```

### Supplier Aggregate (Module 25 / Kernel)

```
Root: ServiceSupplier
Contains: CapabilityAssignment, ResourceAssignment
Boundary: One supplier's marketplace identity and capabilities
Transaction: Supplier activation, capability changes
Events Emitted: Supplier.Created, Supplier.Activated, Capability.Updated
References (not owns): Person, Organization, Schedule
```

### Catalog Aggregate (Catalog Engine)

```
Root: ServiceCategory
Contains: Service, ServicePackage, ServiceOption, ServiceVariant, RequiredCapability, RequiredEquipment, ExecutionRule
Boundary: Service catalog structure
Transaction: Adding/modifying a service and its configuration
Events Emitted: Service.Created, Service.Updated, Category.Changed
```

### Availability Aggregate (Availability Engine)

```
Root: Schedule
Contains: WorkingHours, Holiday, Leave, TemporaryUnavailability, CapacityLimit, EmergencyAvailability
Boundary: One entity's schedule and availability state
Transaction: Schedule changes, leave approvals
Events Emitted: Schedule.Updated, Leave.Approved, Availability.Changed
```

### Order Aggregate (Module 01 + 03)

```
Root: ServiceRequest (M01) / ServiceCase (M03)
Contains: RequestServiceNeed, ServiceRecipient (M01); ServiceAssignment, ExecutionAssignment, ServiceSession, AssignmentPlan (M03)
Boundary: One service request/case and its assignments
Transaction: Request submission, assignment acceptance, session scheduling
Events Emitted: Request.Created, Request.Submitted, Assignment.Created, Session.Scheduled
```

### Execution Aggregate (Module 04)

```
Root: ExecutionSession
Contains: PresenceRecord, StartChecklist, ExecutionActivity, ObservationRecord, EvidenceItem, Interaction, ExecutionException, ExtensionRequest, CompletionRecord, HandoverRecord
Boundary: One active service execution and all its operational records
Transaction: Session state changes, evidence capture
Events Emitted: Session.Started, Session.Completed, Exception.Created
```

### Financial Aggregate (Module 05)

```
Root: FinancialParty
Sub-Aggregates:
  - WalletAccount (root): WalletAccount
  - LedgerJournal (root): LedgerEntry (entries within one journal)
  - FinancialDocument (root): PaymentTransaction
  - SettlementBatch (root): SettlementItem
  - EscrowAccount (root)
Boundary: Financial state of one party
Transaction: Ledger posting (all entries in one journal are atomic)
Events Emitted: Payment.Received, Ledger.Posted, Settlement.Completed
```

### Pricing Aggregate (Pricing Engine)

```
Root: PricePolicy
Contains: PriceComponent, DynamicPricingRule, CommissionPolicy
Boundary: One pricing policy and its components
Transaction: Policy version changes
Events Emitted: PricePolicy.Activated, Commission.Changed
Produces: PriceCalculation (immutable output, separate from aggregate)
```

### Trust Aggregate (Module 06)

```
Root: TrustCase
Contains: Evidence, CaseDecision, EnforcementAction, Appeal
Sub-Aggregates:
  - Review (root): Rating
  - ReputationProfile (root, continuously updated)
Boundary: One governance case or one review
Transaction: Case decisions, enforcement actions
Events Emitted: Review.Submitted, Case.Decided, Enforcement.Applied
```

### Communication Aggregate (Module 07 + 12)

```
Root: CommunicationSession (M07)
Contains: resolved recipients, channel selections, template bindings
Sub-Aggregates:
  - CommunicationDeliveryJob (M12, root): delivery attempts, status
  - InboxItem (M07, root)
  - Conversation (M07, root): messages
Boundary: One communication decision and its delivery
Transaction: Session creation (M07); delivery attempt (M12, separate)
Events Emitted: Communication.SessionCreated, Notification.Delivered
```

### Configuration Aggregate (Module 19 / Kernel)

```
Root: ConfigurationKey
Contains: ConfigurationValue (tenant overrides)
Sub-Aggregates:
  - FeatureFlag (root): targeting rules, evaluations
  - PolicyDefinition (root): PolicyVersion
Boundary: One config key and its scoped values
Transaction: Config value change (audited)
Events Emitted: Config.Changed, Flag.Toggled, Policy.Activated
```

---

### Cross-Aggregate Communication Rules

1. Aggregates communicate **only via CES events** (eventual consistency)
2. An aggregate may **reference** another aggregate's root ID (UUID FK) but never its internal entities
3. A single database transaction may touch **only one aggregate** (except for the event outbox which co-transacts)
4. Queries may **read across aggregates** (read models / projections) but never write across boundaries
5. If a business operation spans aggregates, it is modeled as a **Saga/Process Manager** (Module 16 Workflow)

---

<a id="deliverable-12"></a>
## Deliverable 12 — Entity Lifecycle Diagrams

### ServiceSupplier Lifecycle

```
[pending] ──verify/approve──→ [active] ──suspend──→ [suspended]
                                 │                        │
                                 │ deactivate             │ restore
                                 ▼                        ▼
                           [deactivated]              [active]

Triggers:
  pending → active:    Identity verified + profile approved (M08 event)
  active → suspended:  Trust enforcement (M06 event) or admin action
  suspended → active:  Appeal approved (M06) or admin restore
  active → deactivated: Voluntary deactivation or permanent ban
```

### Order (ServiceRequest) Lifecycle

```
[draft] ──submit──→ [submitted] ──approve──→ [approved] ──publish──→ [published]
   │                     │                                       │
   │ discard             │ reject                                │ match
   ▼                     ▼                                       ▼
[discarded]          [rejected]                             [matched] ──assign──→ [assigned]
                                                                                      │
                                                                              close    │ complete
                                                                                ▼     ▼
                                                                          [closed] [completed]

Cancel from: submitted, approved, published, matched → [cancelled]
Expire from: published (no match within window) → [expired]
```

### ServiceAssignment Lifecycle

```
[created] ──offer──→ [offered] ──accept──→ [accepted] ──activate──→ [active]
                         │                                             │
                         │ decline/expire                              │ complete
                         ▼                                             ▼
                    [declined/expired]                            [completed]
                    
Reassign from: offered, accepted → [reassigned]
Cancel from: created, offered, accepted, active → [cancelled]
```

### ExecutionSession Lifecycle

```
[ready] → [en_route] → [arrived] → [started] → [in_progress] → [completed_by_provider]
                                                      │                    │
                                                      │ pause              │ confirm
                                                      ▼                    ▼
                                                  [paused]          [confirmed] → [closed]
                                                      │
                                                      │ resume
                                                      ▼
                                                [in_progress]

Interrupt from: started, in_progress → [interrupted]
Dispute from: completed_by_provider → [disputed] → [resolved] → [closed]
```

### FinancialDocument (Invoice) Lifecycle

```
[drafted] ──issue──→ [issued] ──pay──→ [paid] ──post──→ [posted] ──close──→ [closed]
              │           │
              │ cancel    │ overdue
              ▼           ▼
         [cancelled]  [overdue] ──pay──→ [paid]
         
Correction from: issued → [corrected] (new document created)
Void from: issued, paid (before post) → [voided]
```

### Settlement Lifecycle

```
[created] ──schedule──→ [scheduled] ──process──→ [processing] ──complete──→ [completed]
                                                       │
                                                       │ fail
                                                       ▼
                                                  [failed] ──retry──→ [processing]
                                                       │
                                                       │ exceed_retries
                                                       ▼
                                                  [dead_letter]
```

### Organization Lifecycle

```
[pending] ──approve──→ [approved] ──activate──→ [active] ──suspend──→ [suspended]
    │                                              │                       │
    │ reject                                       │ dissolve              │ restore
    ▼                                              ▼                       ▼
[rejected]                                   [dissolved]              [active]
```

### OrganizationMembership Lifecycle

```
[invited] ──accept──→ [active] ──suspend──→ [suspended] ──restore──→ [active]
    │                     │                                               
    │ decline             │ terminate                                     
    ▼                     ▼                                               
[declined]          [terminated]
```

### Review Lifecycle

```
[submitted] ──moderate──→ [moderated] ──publish──→ [published]
     │                         │                       │
     │ auto_approve            │ reject                │ hide (violation)
     ▼                         ▼                       ▼
[published]               [rejected]              [hidden]

Appeal from: rejected, hidden → [appealing] → [published] or [rejected]
```

### Document Lifecycle

```
[uploaded] ──process──→ [processing] ──ready──→ [ready] ──archive──→ [archived]
                              │                    │
                              │ fail               │ delete (soft)
                              ▼                    ▼
                         [failed]             [deleted]

Verification path: [ready] ──verify──→ [verified] or [rejected]
```

### Configuration/Policy Lifecycle

```
PolicyDefinition: [draft] → [active] → [deprecated] → [archived]
PolicyVersion:    [draft] → [pending_approval] → [active] → [superseded]

Only one version active at a time per policy.
Superseded versions are immutable historical records.
```

### Notification Lifecycle

```
[queued] ──send──→ [sending] ──deliver──→ [delivered] ──read──→ [read]
                       │
                       │ fail
                       ▼
                  [failed] ──retry──→ [sending]
                       │
                       │ permanent_fail
                       ▼
                  [permanently_failed]
```

---


<a id="deliverable-13"></a>
## Deliverable 13 — Cardinality Matrix

### Core Entity Relationships

| Relationship | Cardinality | Notes |
|---|---|---|
| Tenant → Organization | 1:N | A tenant may have many organizations |
| Tenant → Person | 1:N | A tenant may have many persons |
| Tenant → ServiceCategory | 1:N | Each tenant has its own catalog tree |
| Tenant → ConfigurationValue | 1:N | Per-tenant config overrides |
| Tenant → FeatureFlag | 1:N | Per-tenant flags |
| Person → UserAccount | 1:N | One person may have multiple login accounts |
| Person → OrganizationMembership | 1:N | One person may belong to many orgs |
| Person → RoleAssignment | 1:N | One person may hold many roles |
| Person → CustomerProfile | 1:0..1 | Optional customer profile |
| Person → IndependentProviderProfile | 1:0..1 | Optional independent provider profile |
| Person → OrganizationProviderProfile | 1:0..1 | Optional org-provider profile |
| Person → PlatformStaffProfile | 1:0..1 | Optional platform staff profile |
| Person → Skill | 1:N | Person may have many skills |
| Person → Certification | 1:N | Person may have many certifications |
| Person → Leave | 1:N | Person may have many leave records |
| UserAccount → Credential | 1:N | Multiple auth methods per account |
| Organization → Branch | 1:N | Multi-branch organizations |
| Organization → OrganizationMembership | 1:N | Many members per org |
| Organization → ServiceSupplier | 1:1 | One supplier record per org |
| Organization → Department | 1:N | Via branches or directly |
| Branch → Department | 1:N | Departments within a branch |
| Branch → BranchAssignment | 1:N | Many people assigned |
| Branch → Address | 1:1 | Each branch has one primary address |
| Branch → ServiceArea | 1:N | Branch may cover multiple areas |
| Branch → Schedule | 1:N | Branch may have multiple schedules |
| Department → Team | 1:N | Teams within departments |
| IndependentProviderProfile → ServiceSupplier | 1:1 | One supplier per profile |
| OrganizationProviderProfile → ServiceSupplier | 1:1 | One supplier per profile |
| ServiceSupplier → CapabilityAssignment | 1:N | Supplier has many capabilities |
| ServiceSupplier → ResourceAssignment | 1:N | Supplier has many resources |
| ServiceSupplier → Schedule | 1:N | Supplier has schedules |
| ServiceSupplier → AvailabilitySlot | 1:N | Computed slots |
| ServiceSupplier → ServiceAssignment | 1:N | Supplier receives many assignments |
| ServiceSupplier → FinancialParty | 1:1 | One financial identity |
| ServiceSupplier → ReputationProfile | 1:1 | One reputation record |
| ServiceCategory → ServiceCategory | 1:N | Self-referential nesting (parent → children) |
| ServiceCategory → Service | 1:N | Category contains many services |
| Service → ServicePackage | 1:N | Service may have packages |
| Service → ServiceOption | 1:N | Service may have options |
| Service → ServiceVariant | 1:N | Service may have variants |
| Service → RequiredCapability | 1:N | Service requires capabilities |
| Service → RequiredDocument | 1:N | Service requires documents |
| Service → RequiredEquipment | 1:N | Service requires equipment |
| Service → PricingTemplate | 1:N | Service may have multiple pricing templates |
| Capability → CapabilityAssignment | 1:N | Capability held by many suppliers |
| CapabilityCategory → Capability | 1:N | Category contains capabilities |
| ServiceRequest → RequestServiceNeed | 1:N | Request has multiple service needs |
| ServiceRequest → ServiceRecipient | 1:1 | One recipient per request |
| ServiceRequest → MatchRound | 1:N | Request may trigger multiple match rounds |
| MatchRound → MatchCandidate | 1:N | Round produces many candidates |
| MatchCandidate → CandidateResponse | 1:0..1 | Candidate may or may not respond |
| ServiceCase → ServiceAssignment | 1:N | Case may have multiple assignments |
| ServiceCase → ServiceSession | 1:N | Case spans many sessions |
| ServiceAssignment → ServiceSupplier | N:1 | Many assignments to one supplier |
| ServiceAssignment → ExecutionAssignment | 1:0..1 | Optional internal execution assignment |
| ServiceSession → ExecutionSession | 1:1 | One execution per session |
| ExecutionSession → PresenceRecord | 1:N | Multiple location checks |
| ExecutionSession → ExecutionActivity | 1:N | Multiple tasks |
| ExecutionSession → EvidenceItem | 1:N | Multiple evidence items |
| ExecutionSession → ExecutionException | 1:N | Zero or more exceptions |
| ExecutionSession → ExtensionRequest | 1:N | Zero or more extensions |
| ExecutionSession → CompletionRecord | 1:1 | One completion record |
| FinancialParty → WalletAccount | 1:N | May have multiple wallets |
| FinancialParty → FinancialDocument | 1:N | Many invoices/documents |
| FinancialParty → LedgerEntry | 1:N | Many ledger entries |
| FinancialDocument → PaymentTransaction | 1:N | Multiple payment attempts |
| SettlementBatch → SettlementItem | 1:N | Batch contains items |
| PricePolicy → PriceComponent | 1:N | Policy has components |
| PricePolicy → PriceCalculation | 1:N | Policy produces calculations |
| PolicyDefinition → PolicyVersion | 1:N | Policy has version history |
| TrustCase → EnforcementAction | 1:N | Case may produce multiple actions |
| Review → Rating | 1:1 | One rating per review |
| CommunicationRule → CommunicationSession | 1:N | Rule triggers many sessions |
| CommunicationSession → CommunicationDeliveryJob | 1:N | Session creates delivery jobs |
| IncentiveCampaign → Promotion | 1:N | Campaign has promotions |
| ReferralRelationship → Reward | 1:N | Referral may earn multiple rewards |
| WorkflowDefinition → WorkflowInstance | 1:N | Definition runs many times |
| WorkflowInstance → WorkflowStep | 1:N | Instance has steps |
| Schedule → WorkingHours | 1:N | Schedule defines daily hours |
| Resource → ResourceAssignment | 1:N | Resource assigned to many suppliers over time |
| ResourceType → Resource | 1:N | Type classifies many resources |

---


<a id="deliverable-14"></a>
## Deliverable 14 — Cross-Module Entity Ownership

Every entity has exactly one **owner module**. No ambiguity is permitted.

### Ownership Matrix

| Entity | Owner Module | Read By | Write By | Event Publisher | Config Owner | Permission Owner | Audit Class | Lifecycle Owner |
|--------|-------------|---------|----------|----------------|--------------|-----------------|-------------|-----------------|
| Tenant | M25 (Kernel) | All | M25 | M25 | M25 | M25 | security | M25 |
| Person | M25 (Kernel) | All | M25, M08 | M25 | M25 | M08 | security | M25 |
| UserAccount | M25 (Kernel) | M08, M07 | M25, M08 | M25 | M25 | M08 | security | M25 |
| Credential | M08 | M08 | M08 | M08 | M08 | M08 | security | M08 |
| Role | M25 (Kernel) | All | M25, M08 | M25 | M25 | M08 | standard | M25 |
| Permission | M25 (Kernel) | All (read) | M25 (register) | M25 | M25 | M08 | standard | M25 |
| RoleAssignment | M25 (Kernel) | M08, All (evaluate) | M08 | M08 | M25 | M08 | security | M08 |
| FeatureFlag | M25 (Kernel) | All (evaluate) | M19 | M19 | M19 | M25 | standard | M19 |
| ConfigurationKey | M25 (Kernel) | All | M25 (register) | M25 | M25 | M25 | standard | M25 |
| ConfigurationValue | M25 (Kernel) | All (resolve) | M19 | M19 | M19 | M25 | standard | M19 |
| PolicyDefinition | M25 (Kernel) | All | Per-module owner | Per-module | Per-module | M25 | standard | Per-module |
| PolicyVersion | M25 (Kernel) | All | Per-module owner | Per-module | Per-module | M25 | standard | Per-module |
| ServiceSupplier | M25 (Kernel) | All (query) | M25, M08 | M25 | M25 | M08 | standard | M25 |
| AuditLog | M25 (Kernel) | M23, Admin | M25 (append) | M25 | M25 | M25 | compliance | M25 |
| EventOutbox | M25 (Kernel) | M23 | M25 | M25 | M25 | M25 | standard | M25 |
| Organization | M08 | M02, M03, M05, M09 | M08 | M08 | M08 | M08 | standard | M08 |
| Branch | M08 | M02, M03, M09, M10 | M08 | M08 | M08 | M08 | standard | M08 |
| Department | M08 | M08 | M08 | M08 | M08 | M08 | standard | M08 |
| Team | M08 | M08 | M08 | M08 | M08 | M08 | standard | M08 |
| OrganizationMembership | M08 | M02, M03, M07 | M08 | M08 | M08 | M08 | standard | M08 |
| BranchAssignment | M08 | M02, M03 | M08 | M08 | M08 | M08 | standard | M08 |
| IndependentProviderProfile | M08 | M02, M09 | M08 | M08 | M08 | M08 | standard | M08 |
| OrganizationProviderProfile | M08 | M02, M09 | M08 | M08 | M08 | M08 | standard | M08 |
| CustomerProfile | M08 | M01, M05 | M08 | M08 | M08 | M08 | standard | M08 |
| CustomerDelegate | M08 | M01, M03 | M08 | M08 | M08 | M08 | standard | M08 |
| TrustedPerson | M08 | M04 | M08 | M08 | M08 | M08 | standard | M08 |
| VerificationRequest | M08 | M06 | M08 | M08 | M08 | M08 | compliance | M08 |
| ServiceCategory | Catalog | M01, M02, M09, M11 | Catalog | Catalog | Catalog | M25 | standard | Catalog |
| Service | Catalog | M01, M02, M03, M09 | Catalog | Catalog | Catalog | M25 | standard | Catalog |
| ServicePackage | Catalog | M01, M09 | Catalog | Catalog | Catalog | M25 | standard | Catalog |
| Capability | Catalog | M02, M09 | Catalog | Catalog | Catalog | M25 | standard | Catalog |
| CapabilityAssignment | M25 (Kernel) | M02 | M25, M08 | M25 | M25 | M08 | standard | M25 |
| Schedule | Availability | M02, M03 | Availability | Availability | Availability | M25 | standard | Availability |
| WorkingHours | Availability | M02, M03 | Availability | Availability | Availability | M25 | standard | Availability |
| Holiday | Availability | M02, M03 | Availability | Availability | Availability | M25 | standard | Availability |
| Leave | Availability | M02, M03 | Availability | Availability | Availability | M25 | standard | Availability |
| CapacityLimit | Availability | M02 | Availability | Availability | Availability | M25 | standard | Availability |
| Address | M10 | M01, M02, M08, M09 | M10 | M10 | M10 | M25 | standard | M10 |
| GeoLocation | M10 | M02, M04, M09 | M10 | M10 | M10 | M25 | standard | M10 |
| ServiceArea | M10 | M02, M09 | M10 | M10 | M10 | M25 | standard | M10 |
| ServiceRequest | M01 | M02, M03 | M01 | M01 | M01 | M08 | standard | M01 |
| RequestServiceNeed | M01 | M02 | M01 | M01 | M01 | M08 | standard | M01 |
| MatchRound | M02 | M03 | M02 | M02 | M02 | M08 | standard | M02 |
| MatchCandidate | M02 | M03 | M02 | M02 | M02 | M08 | standard | M02 |
| ServiceCase | M03 | M04, M05 | M03 | M03 | M03 | M08 | standard | M03 |
| ServiceAssignment | M03 | M04, M05, M07 | M03 | M03 | M03 | M08 | standard | M03 |
| ExecutionAssignment | M03 | M04 | M03 | M03 | M03 | M08 | standard | M03 |
| ServiceSession | M03 | M04, M05 | M03 | M03 | M03 | M08 | standard | M03 |
| ExecutionSession | M04 | M05, M06 | M04 | M04 | M04 | M08 | standard | M04 |
| PresenceRecord | M04 | M06 | M04 | M04 | M04 | M08 | standard | M04 |
| EvidenceItem | M04 | M06, M13 | M04 | M04 | M04 | M08 | standard | M04 |
| ExecutionException | M04 | M06, M07 | M04 | M04 | M04 | M08 | standard | M04 |
| CompletionRecord | M04 | M05 | M04 | M04 | M04 | M08 | standard | M04 |
| FinancialParty | M05 | M11 | M05 | M05 | M05 | M08 | financial | M05 |
| WalletAccount | M05 | — | M05 | M05 | M05 | M08 | financial | M05 |
| LedgerEntry | M05 | M17 | M05 (append-only) | M05 | M05 | M08 | financial | M05 |
| FinancialDocument | M05 | M07 | M05 | M05 | M05 | M08 | financial | M05 |
| PaymentTransaction | M05 | — | M05 | M05 | M05 | M08 | financial | M05 |
| SettlementBatch | M05 | — | M05 | M05 | M05 | M08 | financial | M05 |
| EscrowAccount | M05 | — | M05 | M05 | M05 | M08 | financial | M05 |
| PricePolicy | Pricing | M02, M05 | Pricing | Pricing | Pricing | M25 | standard | Pricing |
| PriceComponent | Pricing | M05 | Pricing | Pricing | Pricing | M25 | standard | Pricing |
| CommissionPolicy | Pricing | M05, M11 | Pricing | Pricing | Pricing | M25 | financial | Pricing |
| Coupon | Pricing | M01 | Pricing, M11 | Pricing | Pricing | M25 | standard | Pricing |
| TrustCase | M06 | M07 | M06 | M06 | M06 | M08 | compliance | M06 |
| Review | M06 | M09, M14 | M06 | M06 | M06 | M08 | standard | M06 |
| ReputationProfile | M06 | M02, M09 | M06 | M06 | M06 | M08 | standard | M06 |
| EnforcementAction | M06 | M08, M07 | M06 | M06 | M06 | M08 | compliance | M06 |
| CommunicationRule | M07 | — | M07 | M07 | M07 | M08 | standard | M07 |
| CommunicationSession | M07 | M12 | M07 | M07 | M07 | M08 | standard | M07 |
| CommunicationDeliveryJob | M12 | M07 | M12 | M12 | M12 | M08 | standard | M12 |
| Notification | M12 | M07 | M12 | M12 | M12 | M08 | standard | M12 |
| InboxItem | M07 | — | M07 | M07 | M07 | M08 | standard | M07 |
| IncentiveCampaign | M11 | M09 | M11 | M11 | M11 | M08 | standard | M11 |
| Promotion | M11 | M01, Pricing | M11 | M11 | M11 | M08 | standard | M11 |
| ReferralRelationship | M11 | M05 | M11 | M11 | M11 | M08 | standard | M11 |
| Document | M13 | M01, M04, M06, M08 | M13 | M13 | M13 | M08 | standard | M13 |
| Resource | Catalog | M02, M04 | Catalog | Catalog | Catalog | M25 | standard | Catalog |
| ResourceAssignment | M25 (Kernel) | M02 | M25 | M25 | M25 | M08 | standard | M25 |
| WorkflowDefinition | M16 | — | M16 | M16 | M16 | M08 | standard | M16 |
| WorkflowInstance | M16 | All (subscribe) | M16 | M16 | M16 | M08 | standard | M16 |
| SearchIndex | M09 | — | M09 | M09 | M09 | M25 | standard | M09 |
| Theme | M25 (Kernel) | All (render) | M25 | M25 | M19 | M25 | standard | M25 |
| Locale | M24 | All | M24 | M24 | M24 | M25 | standard | M24 |
| TranslationEntry | M24 | All (render) | M24 | M24 | M24 | M25 | standard | M24 |
| HealthCheck | M23 | Admin | M23 | M23 | M23 | M25 | standard | M23 |
| Alert | M23 | Admin | M23 | M23 | M23 | M25 | standard | M23 |
| IntegrationEndpoint | M18 | — | M18 | M18 | M18 | M08 | standard | M18 |
| Plan | M21 | M05, M08 | M21 | M21 | M21 | M08 | standard | M21 |
| Subscription | M21 | M05, M08, M19 | M21 | M21 | M21 | M08 | financial | M21 |
| JobExecution | M22 | M23 | M22 | M22 | M22 | M25 | standard | M22 |
| AIModel | M20 | M02 | M20 | M20 | M20 | M08 | standard | M20 |
| Recommendation | M20 | M02, M09 | M20 | M20 | M20 | M08 | standard | M20 |

---


<a id="deliverable-15"></a>
## Deliverable 15 — PostgreSQL Schema Layout

### Schema Separation Strategy

All tables are organized into **PostgreSQL schemas** (not the `public` schema). Each schema corresponds to a bounded context or module group.

```sql
-- Schema creation (executed in migration 0001)
CREATE SCHEMA IF NOT EXISTS kernel;
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS organizations;
CREATE SCHEMA IF NOT EXISTS catalog;
CREATE SCHEMA IF NOT EXISTS availability;
CREATE SCHEMA IF NOT EXISTS pricing;
CREATE SCHEMA IF NOT EXISTS marketplace;
CREATE SCHEMA IF NOT EXISTS orders;
CREATE SCHEMA IF NOT EXISTS execution;
CREATE SCHEMA IF NOT EXISTS financial;
CREATE SCHEMA IF NOT EXISTS communication;
CREATE SCHEMA IF NOT EXISTS trust;
CREATE SCHEMA IF NOT EXISTS documents;
CREATE SCHEMA IF NOT EXISTS incentives;
CREATE SCHEMA IF NOT EXISTS search;
CREATE SCHEMA IF NOT EXISTS geospatial;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS integration;
CREATE SCHEMA IF NOT EXISTS workflow;
CREATE SCHEMA IF NOT EXISTS jobs;
CREATE SCHEMA IF NOT EXISTS observability;
CREATE SCHEMA IF NOT EXISTS localization;
CREATE SCHEMA IF NOT EXISTS audit;
```

### Schema → Table Mapping

| Schema | Tables | Owner Module(s) |
|--------|--------|----------------|
| `kernel` | tenant, person, user_account, role, permission, role_assignment, feature_flag, configuration_key, configuration_value, policy_definition, policy_version, service_supplier, capability_assignment, resource_assignment, event_outbox, theme, theme_override, correlation_context | M25 |
| `identity` | credential, session, identity_verification, profile_field, customer_profile, independent_provider_profile, organization_provider_profile, platform_staff_profile, customer_delegate, trusted_person, verification_request, skill, certification | M08 |
| `organizations` | organization, branch, department, team, organization_membership, branch_assignment | M08 |
| `catalog` | service_category, service, service_package, package_item, service_option, option_choice, service_variant, service_attribute, service_unit, pricing_template, required_capability, required_document, required_equipment, execution_rule, capability_category, capability, resource_type, resource, resource_requirement | Catalog |
| `availability` | schedule, working_hours, holiday, leave, temporary_unavailability, capacity_limit, emergency_availability, availability_slot | Availability |
| `pricing` | price_policy, price_component, price_calculation, discount, coupon, tax_rule, insurance_fee, commission_policy, dynamic_pricing_rule | Pricing |
| `marketplace` | visibility_policy, matching_config | M02 + M19 |
| `orders` | service_request, request_service_need, service_recipient, match_round, match_candidate, candidate_response, customer_selection, eligibility_evaluation, ranking_score, service_case, service_assignment, execution_assignment, service_session, assignment_plan | M01, M02, M03 |
| `execution` | execution_session, presence_record, start_checklist, execution_activity, observation_record, evidence_item, interaction, execution_exception, extension_request, completion_record, handover_record | M04 |
| `financial` | financial_party, commercial_contract, financial_document, payment_transaction, wallet_account, escrow_account, ledger_entry, ledger_journal, settlement_batch, settlement_item, financial_reservation, refund, adjustment, financial_obligation | M05 |
| `communication` | communication_rule, communication_session, communication_delivery_job, communication_template, communication_preference, inbox_item, conversation, notification, reminder, campaign | M07, M12 |
| `trust` | trust_case, review, rating, reputation_profile, complaint, dispute, enforcement_action, appeal, risk_signal | M06 |
| `documents` | document, document_version, media_asset, document_requirement, signature | M13 |
| `incentives` | incentive_campaign, promotion, promotion_application, referral_relationship, reward, commission_adjustment | M11 |
| `search` | search_index, searchable_document, facet_definition, ranking_profile, saved_search | M09 |
| `geospatial` | address, geo_location, service_area, geofence_rule, route_estimate, live_location_session | M10 |
| `analytics` | metric_definition, dashboard, report, data_export | M17 |
| `integration` | integration_endpoint, integration_credential, webhook_subscription, integration_log | M18 |
| `workflow` | workflow_definition, workflow_instance, workflow_step, workflow_timer | M16 |
| `jobs` | job_definition, job_execution, job_schedule | M22 |
| `observability` | health_check, alert, incident, slo_definition | M23 |
| `localization` | locale, translation_entry, calendar_system | M24 |
| `audit` | audit_log (partitioned by month) | M25 |

### Cross-Schema References

Foreign keys may cross schemas (PostgreSQL supports this natively). The pattern:

```sql
-- Example: orders schema referencing kernel schema
ALTER TABLE orders.service_assignment
    ADD CONSTRAINT fk_assignment_supplier
    FOREIGN KEY (supplier_id) REFERENCES kernel.service_supplier(id);
```

### Key Schema Rules

1. **No table in `public` schema** — all business tables live in named schemas
2. **Django migrations manage all schemas** — use `db_table = 'schema.table_name'` in Meta
3. **Search path** for Django: `SET search_path TO kernel, identity, organizations, catalog, ...`
4. **Each schema has independent index namespace** — no index name collisions
5. **Partitioned tables** (audit_log, event_outbox) stay in their owning schema

---

<a id="deliverable-16"></a>
## Deliverable 16 — Shared Kernel Entity Catalog

### Definition

The **Shared Kernel** (Module 25) contains entities that:
- Are referenced by multiple modules
- Have platform-wide scope (not module-specific)
- Define cross-cutting contracts
- Must remain stable across all module versions

### Shared Kernel Entities

| Entity | Why It's Shared | Referenced By |
|--------|----------------|---------------|
| **Tenant** | Every tenant-aware entity references it | All modules |
| **Person** | Stable identity across all roles/contexts | M08, M01, M02, M03, M04, M05, M06, M07 |
| **UserAccount** | Authentication across all portals | M08, Auth system |
| **Role** | Permission evaluation for all operations | All modules (via M08 evaluation) |
| **Permission** | Protected operations registry | All modules register; M08 evaluates |
| **RoleAssignment** | Access decisions for all modules | M08 evaluates for all |
| **ServiceSupplier** | Universal supply-side interface | M01, M02, M03, M04, M05, M06, M07, M09, M11, M14 |
| **CapabilityAssignment** | Supplier capabilities for matching | M02, M09 |
| **ResourceAssignment** | Supplier resources for matching | M02, M04 |
| **ConfigurationKey** | Configuration contract definitions | All modules |
| **ConfigurationValue** | Runtime configuration resolution | All modules |
| **FeatureFlag** | Feature toggle evaluation | All modules |
| **PolicyDefinition** | Policy governance envelope | All modules with policies |
| **PolicyVersion** | Immutable policy snapshots | All modules with policies |
| **AuditLog** | Cross-module audit trail | M23, Admin, Compliance |
| **EventOutbox** | Cross-module event publishing | All modules (produce); consumers (consume) |
| **Theme** | UI rendering across all portals | Frontend rendering |
| **ThemeOverride** | Tenant-specific branding | Frontend rendering |
| **CorrelationContext** | Request tracing | All modules, M23 |

### Shared Kernel Contracts (Not Entities, But Equally Binding)

| Contract | What It Defines |
|----------|----------------|
| CES Event Envelope | Shape of all published events |
| CCS Configuration Envelope | Shape of all config keys/values |
| Global Identifier Standard | UUID + required metadata on all entities |
| Shared Error Model | Error response structure for all APIs |
| Audit Envelope Standard | Shape of all audit records |
| API Contract Conventions | REST conventions for all endpoints |
| Tenant Boundary Standard | Isolation rules for all queries |
| Permission Boundary Standard | How permission evaluation works |

### Kernel Dependency Rule (Absolute)

```
Module 25 (Kernel) → depends on NOTHING
All other modules → may depend on Module 25
No module → may bypass Kernel contracts
```

---

<a id="deliverable-17"></a>
## Deliverable 17 — Migration Strategy

### Versioning

| Principle | Implementation |
|-----------|---------------|
| Sequential numbering | Django migration auto-numbering (0001_, 0002_, ...) per app |
| One app per bounded context | Each module has its own migration history |
| Dependencies declared | Migration files declare inter-app dependencies explicitly |
| Version in model | Every entity has `version` field for optimistic concurrency |

### Backward Compatibility Rules

1. **Never remove a column** in a production migration — add `deprecated_at` timestamp first
2. **Never rename a column** directly — add new column, migrate data, deprecate old
3. **Never change column type** destructively — add new column if type must change
4. **Never drop a table** — move to archive schema or rename with `_deprecated` suffix
5. **All new columns must have defaults** or be nullable (for zero-downtime deploy)
6. **Index creation uses CONCURRENTLY** where possible

### Data Migration Strategy

```
Phase 1: Schema migration (add new structure)
Phase 2: Data migration (backfill new columns/tables)
Phase 3: Code migration (switch reads to new structure)
Phase 4: Cleanup migration (remove deprecated after grace period)
```

### Soft Delete Strategy

```python
class SoftDeleteModel(models.Model):
    """Mixin for soft-deletable entities."""
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.UUIDField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self, actor_id=None):
        self.deleted_at = timezone.now()
        self.deleted_by = actor_id
        self.save(update_fields=['deleted_at', 'deleted_by', 'updated_at'])

    @property
    def is_deleted(self):
        return self.deleted_at is not None
```

Default manager excludes soft-deleted records:
```python
class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)
```

### Archive Strategy

| Data Type | Archive After | Archive To | Retention |
|-----------|--------------|-----------|-----------|
| Audit logs | 90 days | Partitioned cold table | 7 years |
| Event outbox (published) | 30 days | Archive table | 1 year |
| Execution evidence | 1 year | Object storage | 5 years |
| Financial documents | Never auto-archive | — | Permanent |
| Completed sessions | 1 year | Archive schema | 5 years |
| Notifications (delivered) | 90 days | Archive table | 1 year |
| Search logs | 30 days | Analytics schema | 1 year |

### Partitioning Strategy

| Table | Partition Key | Partition Interval | Rationale |
|-------|--------------|-------------------|-----------|
| `audit.audit_log` | `occurred_at` | Monthly | High write volume, time-series queries |
| `kernel.event_outbox` | `created_at` | Weekly | High throughput, short retention |
| `execution.presence_record` | `created_at` | Monthly | High volume GPS records |
| `analytics.metric_*` | `recorded_at` | Monthly | Time-series analytics |
| `communication.notification` | `created_at` | Monthly | High volume, time queries |

### Index Strategy

| Pattern | When to Use | Example |
|---------|------------|---------|
| B-tree (default) | Equality/range on scalar | `tenant_id`, `status`, `created_at` |
| GIN | JSONB containment/existence | `capabilities @> '{"ICU": true}'` |
| GiST | Geospatial queries | `geography(Point, 4326)` |
| Trigram (pg_trgm) | Text search / fuzzy match | `name gin_trgm_ops` |
| Partial | Conditional subset | `WHERE status = 'active'` |
| Covering | Avoid table lookups | `INCLUDE (name, status)` |
| Composite | Multi-column queries | `(tenant_id, supplier_type, status)` |

### Zero-Downtime Migration

```
1. Deploy new code that handles BOTH old and new schema
2. Run migration (online, non-locking where possible)
3. Backfill data if needed (background job)
4. Deploy code that only uses new schema
5. Drop deprecated columns (grace period later)
```

Django-specific:
- Use `AddIndex` with `create_concurrently=True` (Django 4.0+)
- Use `RunSQL` for complex schema changes that need `IF NOT EXISTS`
- Never run data migrations in the same transaction as schema changes

### Rollback Strategy

| Scenario | Rollback Method |
|----------|----------------|
| Failed schema migration | `python manage.py migrate app_name previous_migration` |
| Failed data migration | Reverse data migration function (always write reverse) |
| Failed deploy | Blue-green switch back to previous version |
| Data corruption | Point-in-time recovery from PostgreSQL WAL backup |
| Partial failure | Per-app migration rollback (apps are independent) |

---

<a id="deliverable-18"></a>
## Deliverable 18 — Architecture Validation

### Validation Checklist

The frozen domain model must support **all** of the following scenarios without requiring schema redesign, model refactoring, or migration changes:

| # | Scenario | How Supported |
|---|----------|---------------|
| ✅ 1 | **Independent-provider marketplace** | `marketplace.supplier_model = independent_only`; ServiceSupplier with type=INDEPENDENT_PROVIDER; Matching filters by config; Financial pays supplier directly |
| ✅ 2 | **Organization-only marketplace** | `marketplace.supplier_model = organization_only`; Organizations are suppliers; ExecutionAssignment for internal provider; Financial pays organization |
| ✅ 3 | **Hybrid marketplace** | `marketplace.supplier_model = hybrid`; Both supplier types active; VisibilityPolicy controls ordering; All modules handle both types |
| ✅ 4 | **Multiple industries** | ServiceCategory tree is tenant-data; Capability system is generic; No industry-specific code; Display labels from localization |
| ✅ 5 | **White-label SaaS** | Tenant isolation; Theme/ThemeOverride per tenant; Branding in org settings; Domain mapping on Tenant; All labels from translation layer |
| ✅ 6 | **Multi-tenant deployment** | `tenant_id` on all business tables; TenantAwareModel base; Tenant middleware; Schema isolation; Cross-tenant denied by default |
| ✅ 7 | **Multi-language** | Module 24 Locale system; TranslationEntry per string; Calendar-independent dates; All user text from translation catalog |
| ✅ 8 | **Multiple calendars** | CalendarSystem entity; Backend stores UTC Gregorian; Frontend converts via M24; Jalali, Hijri, Gregorian all data-driven |
| ✅ 9 | **Multiple currencies** | `currency` field on all financial entities; PriceComponent has currency; CommissionPolicy currency-aware; No hardcoded Rial/Toman |
| ✅ 10 | **Multiple pricing policies** | PricePolicy versioned, scoped, per-service/category/tenant; PriceComponent composable; DynamicPricingRule configurable |
| ✅ 11 | **Multiple commission policies** | CommissionPolicy versioned with tiers; Per supplier_type, category, service; Platform + org commission independent |
| ✅ 12 | **Future AI modules** | AIModel, Recommendation, Prediction entities; M20 consumes events from all modules; HumanOverride audit; Model governance built-in |
| ✅ 13 | **Future mobile applications** | REST API with JWT; All business logic in services (not views); API versioning; No template-coupled logic |
| ✅ 14 | **Future API consumers** | OpenAPI schema; Module 18 Integration Engine; WebhookSubscription; Rate limiting; API key management |
| ✅ 15 | **Enterprise-scale deployment** | Partitioned tables; Redis caching; Celery async; Event-driven (no sync cross-module calls); Read replicas possible; Horizontal scaling via stateless web tier |

### Additional Validation Points

| # | Validation | Status |
|---|-----------|--------|
| ✅ 16 | A person can be Customer + Provider simultaneously | Person → multiple profiles → multiple suppliers |
| ✅ 17 | An organization can have 100 branches without schema change | Branch is 1:N from Organization, no limit in schema |
| ✅ 18 | A service can require 10 capabilities | RequiredCapability is 1:N from Service |
| ✅ 19 | Pricing can change per time-of-day, season, demand | DynamicPricingRule with trigger_conditions JSONB |
| ✅ 20 | Matching can use AI without code change | VisibilityStrategy = 'ai_recommendation'; M20 provides rankings |
| ✅ 21 | A new service type can be added without migration | ServiceCategory and Service are data rows, not code |
| ✅ 22 | A new capability can be added without migration | Capability is a data row, not an enum |
| ✅ 23 | A new resource type can be added without migration | ResourceType is a data row with attributes_schema JSONB |
| ✅ 24 | Commission can vary per supplier type | CommissionPolicy.target_type = 'supplier_type' |
| ✅ 25 | Organization internal compensation is separate | Financial pays org; org handles internal compensation via own systems or future policy |
| ✅ 26 | Reviews can target supplier OR execution provider | Review.target_type polymorphic; handles both |
| ✅ 27 | Notifications route differently per supplier type | M07 resolves recipients using supplier_type + policy |
| ✅ 28 | Feature flags can be per-tenant, per-actor, percentage | FeatureFlag.flag_type + targeting_rules JSONB |
| ✅ 29 | Audit logs are immutable and partitioned | Append-only model; monthly partitioning; no UPDATE/DELETE |
| ✅ 30 | Events are transactionally consistent with state | Outbox pattern: state + event in one DB transaction |

### Architecture Freeze Declaration

This document establishes the **frozen enterprise domain model**. The following are now binding:

1. Entity names and their owning modules (Deliverable 14)
2. Aggregate boundaries and transaction rules (Deliverable 11)
3. Cardinality relationships (Deliverable 13)
4. PostgreSQL schema layout (Deliverable 15)
5. Shared Kernel contents (Deliverable 16)
6. Lifecycle state machines (Deliverable 12)
7. Supplier abstraction pattern (Deliverable 1 + Architecture Intake Report Section 16)
8. Identity model (Person ≠ User ≠ Provider, Deliverable 2)
9. Branch architecture (Deliverable 4)
10. Service Catalog hierarchy (Deliverable 5)
11. Capability separation from categories (Deliverable 6)
12. Availability as independent subsystem (Deliverable 7)
13. Pricing separated from Financial Operations (Deliverable 8)
14. Visibility as configurable policy (Deliverable 10)
15. Migration strategy (Deliverable 17)

**No production code may be written until this document is approved.**

Once approved, Phase 1 implementation proceeds with this frozen model as its blueprint.

---

*End of Phase 0.5 — Enterprise Domain Model Freeze*
