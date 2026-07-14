# Architecture Intake Report v1.0

## Enterprise Service Marketplace Platform — Phase 0 Deliverable

**Date:** July 6, 2026
**Author:** Platform Architecture Team (AI-Assisted)
**Status:** ✅ Approved — All Blocking Decisions Resolved
**Scope:** Full review of all 25 module specifications + Framework Architecture Correction Package

---

## Table of Contents

1. [Document Review Confirmation](#1-document-review-confirmation)
2. [Discovered Modules & Discrepancies](#2-discovered-modules--discrepancies)
3. [Extracted Domain Entities](#3-extracted-domain-entities)
4. [Extracted Dependencies (Module Ownership Map)](#4-extracted-dependencies)
5. [Extracted Events](#5-extracted-events)
6. [Extracted Configurations](#6-extracted-configurations)
7. [Extracted Permissions / Protected Operations](#7-extracted-permissions)
8. [Extracted Policies](#8-extracted-policies)
9. [UI/UX Kernel Plan](#9-uiux-kernel-plan)
10. [Persian RTL/Jalali Implementation Plan](#10-persian-rtljalali-plan)
11. [Confirmed Technology Stack](#11-confirmed-technology-stack)
12. [Proposed Database Architecture](#12-proposed-database-architecture)
13. [Implementation Phases](#13-implementation-phases)
14. [Risks and Missing Information](#14-risks-and-missing-information)
15. [Questions Requiring Human Approval](#15-questions-requiring-human-approval)
16. [Supplier Abstraction and Marketplace Model Variants](#16-supplier-abstraction-and-marketplace-model-variants)

---


## 1. Document Review Confirmation

All 25 module specification packages and the Framework Architecture Correction Package have been reviewed. Below is the complete file inventory:

### Framework Architecture Correction Package v1.0
| File | Status |
|------|--------|
| `README.md` | ✅ Reviewed |
| `01_STANDARDS/Canonical_Actor_Glossary.md` | ✅ Reviewed |
| `01_STANDARDS/CES_Event_Naming_Standard.md` | ✅ Reviewed |
| `01_STANDARDS/CCS_Configuration_Naming_Standard.md` | ✅ Reviewed |
| `02_CROSS_MODULE/Communication_Ownership_Cleanup.md` | ✅ Reviewed |
| `02_CROSS_MODULE/Dependency_Map.md` | ✅ Reviewed |
| `02_CROSS_MODULE/Permission_Ownership_Model.md` | ✅ Reviewed |
| `02_CROSS_MODULE/Trust_vs_Identity_Boundary.md` | ✅ Reviewed |
| `03_FREEZE/Modules_01_to_08_Freeze_Gate.md` | ✅ Reviewed |
| `04_REFERENCE_IMPLEMENTATION/Generic_to_Senior_Care_Mapping.md` | ✅ Reviewed |

### Module 25 — Platform Kernel (20 files)
| File | Status |
|------|--------|
| `README.md` | ✅ Reviewed |
| `01_Architecture/Enterprise_Architecture_Specification.md` | ✅ Reviewed |
| `01_Architecture/Module_Boundary_Map.md` | ✅ Reviewed |
| `02_Shared_Contracts/Global_Identifier_Standard.md` | ✅ Reviewed |
| `02_Shared_Contracts/Shared_Error_Model.md` | ✅ Reviewed |
| `02_Shared_Contracts/API_Contract_Conventions.md` | ✅ Reviewed |
| `03_Canonical_Model/Canonical_Data_Model.md` | ✅ Reviewed |
| `03_Canonical_Model/Tenant_Boundary_Standard.md` | ✅ Reviewed |
| `04_Event_Kernel/CES_Kernel_Envelope.md` | ✅ Reviewed |
| `04_Event_Kernel/CES_Global_Event_Catalog.md` | ✅ Reviewed |
| `05_Config_Kernel/CCS_Kernel_Envelope.md` | ✅ Reviewed |
| `05_Config_Kernel/CCS_Global_Configuration_Catalog.md` | ✅ Reviewed |
| `06_Security_Access/Permission_Boundary_Standard.md` | ✅ Reviewed |
| `06_Security_Access/Privacy_Classification_Standard.md` | ✅ Reviewed |
| `07_Dependency_Governance/Dependency_Rules.md` | ✅ Reviewed |
| `07_Dependency_Governance/Cross_Module_Contract_Registry.md` | ✅ Reviewed |
| `08_Compatibility_Versioning/Versioning_Migration_Rules.md` | ✅ Reviewed |
| `08_Compatibility_Versioning/Compatibility_Matrix.md` | ✅ Reviewed |
| `09_Observability_Audit/Audit_Envelope_Standard.md` | ✅ Reviewed |
| `09_Observability_Audit/Trace_Correlation_Standard.md` | ✅ Reviewed |
| `10_Testing_Acceptance/Acceptance_Criteria.md` | ✅ Reviewed |


### Modules 01–08 (Core Business Modules — Correction Package applies)
| Module | Folder | Files | Freeze Status |
|--------|--------|-------|---------------|
| 01 — Request Engine | `Senior_Platform_Module_01_Request_Engine_v1.0/` | 17 docs + addendum | ✅ Frozen |
| 02 — Matching Engine | `Senior_Platform_Module_02_Matching_Engine_v1.0/` | 17 docs + addendum | ✅ Frozen |
| 03 — Booking/Assignment Engine | `Senior_Platform_Module_03_Booking_Assignment_Engine_v1.0/` | 18+ docs + addendum | ✅ Frozen |
| 04 — Service Execution Engine | `Senior_Platform_Module_04_Service_Execution_Engine_v1.0/` | 28 docs + addendum | ✅ Frozen |
| 05 — Financial Operations Engine | `Senior_Platform_Module_05_Financial_Operations_Engine_v1_1_ENTERPRISE_FINAL/` | 41 docs + addendum | ✅ Frozen (v1.1) |
| 06 — Trust/Governance Engine | `Senior_Platform_Module_06_Trust_Quality_Governance_Engine_v1_0_ENTERPRISE/` | Multi-file enterprise spec | ✅ Frozen |
| 07 — Communication Orchestration | `Senior_Platform_Module_07_Communication_Orchestration_Engine_v1_0/` | 28 docs + README | ✅ Frozen Candidate |
| 08 — Identity/Access Engine | `Senior_Platform_Module_08_Identity_Roles_Profiles_Access_Engine_v1_0/` | 12 directories of specs | ✅ Frozen |

### Modules 09–24 (Platform Capability Modules)
| Module | Folder | Freeze Status |
|--------|--------|---------------|
| 09 — Search, Discovery & Filtering | `Senior_Platform_Module_09_Search_Discovery_Filtering_Engine_v1_0/` | ✅ Frozen |
| 10 — Geospatial, Maps & Location | `Senior_Platform_Module_10_Geospatial_Maps_Location_Engine_v1_0/` | ✅ Frozen |
| 11 — Incentives/Referrals/Promotions/Commission | `Senior_Platform_Module_11_Incentives_Referrals_Promotions_Commission_Policy_Engine_v1_0/` | ✅ Frozen |
| 12 — Communication & Notification | `Senior_Platform_Module_12_Communication_Notification_Engine_v1_0/` | ✅ Frozen |
| 13 — Document, Media & File Management | `Senior_Platform_Module_13_Document_Media_File_Management_Engine_v1_0/` | ✅ Frozen |
| 14 — Review, Rating & Reputation | `Senior_Platform_Module_14_Review_Rating_Reputation_Engine_v1_0/` | ✅ Frozen |
| 15 — Knowledge, CMS & Content | `Senior_Platform_Module_15_Knowledge_CMS_Content_Engine_v1_0/` | ✅ Frozen |
| 16 — Workflow & Automation | `Senior_Platform_Module_16_Workflow_Automation_Engine_v1_0/` | ✅ Frozen |
| 17 — Analytics, Reporting & BI | `Senior_Platform_Module_17_Analytics_Reporting_BI_Engine_v1_0/` | ✅ Frozen |
| 18 — Integration & API Gateway | `Senior_Platform_Module_18_Integration_API_Gateway_Engine_v1_0/` | ✅ Frozen |
| 19 — Platform Configuration & Feature Flag | `Senior_Platform_Module_19_Platform_Configuration_Feature_Flag_Engine_v1_0/` | ✅ Frozen |
| 20 — AI, Recommendation & Decision Intelligence | `Senior_Platform_Module_20_AI_Recommendation_Decision_Intelligence_Engine_v1_0/` | ✅ Frozen |
| 21 — Subscription, Plans & Licensing | `Senior_Platform_Module_21_Subscription_Plans_Licensing_Engine_v1_0/` | ✅ Frozen |
| 22 — Background Jobs & Scheduler | `Senior_Platform_Module_22_Background_Jobs_Scheduler_Engine_v1_0/` | ✅ Frozen |
| 23 — Observability, Monitoring & Health | `Senior_Platform_Module_23_Observability_Monitoring_Health_Engine_v1_0/` | ✅ Frozen |
| 24 — Internationalization & Localization | `Senior_Platform_Module_24_Internationalization_Localization_Engine_v1_0/` | ✅ Frozen |

### Summary Index
| File | Status |
|------|--------|
| `MODULE_INDEX_COMPLETE_01_25.json` | ✅ Reviewed (known stale — see Section 2) |

**Total documents reviewed:** 250+ specification files across 26 packages.


---

## 2. Discovered Modules & Discrepancies

### 2.1 Module 07 Identity Conflict — ✅ RESOLVED

**Finding:** `MODULE_INDEX_COMPLETE_01_25.json` lists Module 7 as "Business Roles & Platform Structure Engine" but the actual folder implements "Communication Orchestration Engine."

**Owner Decision (Approved):**
> Module 07 is **Communication Orchestration Engine**. The "Business Roles & Platform Structure Engine" is not a separate module. Its relevant scope is merged into **Module 08 — Identity, Roles, Profiles & Access Engine**.

**Implementation Rule:** The JSON index entry for Module 7 is stale. All code, documentation, and references must treat Module 7 as Communication Orchestration Engine. Module 08 owns all organization structures, role relationships, platform structure, and business roles.

### 2.2 Module 07 / Module 12 Communication Boundary — ✅ RESOLVED

**Finding:** Both modules cover "communication."

**Owner Decision (Approved):**

| Responsibility | Module 07 (Communication Orchestration) | Module 12 (Communication & Notification) |
|---|---|---|
| Event consumption | ✅ Consumes all business CES events | ❌ Does not consume business events directly |
| Decides WHO to notify | ✅ | ❌ |
| Decides WHEN to notify | ✅ | ❌ |
| Decides WHICH channels | ✅ (based on policy, consent, tenant config, actor context) | ❌ |
| Resolves recipients | ✅ | ❌ |
| Communication intent | ✅ | ❌ |
| Delivery infrastructure | ❌ | ✅ Owns all provider adapters (SMS, email, push, in-app) |
| Delivery attempts/retries | ❌ | ✅ |
| Delivery status tracking | ❌ | ✅ |
| Template rendering | Shared (Module 07 selects; Module 12 renders at delivery time) | ✅ |
| Provider responses/failures | ❌ | ✅ |
| Direct SMS/email/push sending | ❌ Never | ✅ Only when requested via orchestration/delivery contract |

**Binding Rule:** Business modules must NOT call SMS/email providers directly. They emit CES events only. Module 07 orchestrates. Module 12 delivers.

### 2.3 Frontend Technology Stack — ✅ RESOLVED

**Owner Decision (Approved):**

**Django Templates + HTMX/Alpine.js + Tailwind CSS**

| Requirement | Implementation |
|-------------|---------------|
| Persian-first UI | ✅ All templates in Persian, `lang="fa-IR"` `dir="rtl"` |
| Full RTL support | ✅ Tailwind CSS RTL plugin + logical properties |
| Jalali/Shamsi dates | ✅ `jdatetime` backend + Jalali JS picker |
| Shared UI Kernel | ✅ Design tokens via Tailwind config + Django template components |
| Tenant-overridable tokens | ✅ CSS custom properties + CCS config resolution |
| Reusable components | ✅ Django template includes/partials + Alpine.js components |
| No duplicate page styling | ✅ Single Tailwind design system, shared base templates |
| No separate SPA | ✅ Server-rendered with HTMX progressive enhancement |

**Technology Stack Details:**
- **Templates:** Django Template Language with `{% include %}` component pattern
- **Interactivity:** HTMX for server-driven partial updates; Alpine.js for client-side state
- **Styling:** Tailwind CSS 3.x with custom design tokens, RTL plugin, dark-mode ready
- **Build:** Tailwind CLI or PostCSS build step (no webpack/vite complexity needed)
- **Icons:** Heroicons or similar SVG icon system (RTL-mirror-aware)
- **Date Picker:** Custom Jalali date picker (Alpine.js component)

**No separate SPA, no React, no Next.js in this phase.** API endpoints still exist for future mobile/SPA consumption but are not the primary frontend delivery mechanism.

### 2.4 Additional Discrepancies Found

| Issue | Severity | Details |
|-------|----------|---------|
| Module 05 version mismatch | Low | Folder says v1.1, index says v1.0. Content appears to be v1.1 Enterprise Final. |
| Module 06 naming variance | Low | Index: "Trust, Compliance & Governance"; Folder: "Trust_Quality_Governance". Content covers both quality and compliance. |
| Modules 12-24 templated specs | Medium | Modules 12-16 and 17-24 share an identical generic domain model template (Policy, PolicyVersion, RuleSet, EligibilityRule, DecisionTrace, ActionRequest, ActionResult). Differentiation exists primarily in README descriptions and CES event catalogs. This may indicate these modules need domain-specific entity enrichment before implementation. |


---

## 3. Extracted Domain Entities

### Module 01 — Request Engine
| Entity | Description |
|--------|-------------|
| Request | The root aggregate — a service request from intake to handoff |
| RequestServiceNeed | Individual service requirements within a request |
| CareReceiver (Service Recipient) | The person/entity receiving the service |
| RequestOwner | The customer or delegate who owns the request |
| Application | Provider's application/response to a request |
| Contract | Formalized agreement when a request is accepted |
| Session | Planned service session within a contract |
| ProtectionSignal | Risk/fraud indicators attached to requests |
| RequestEvent | Immutable event log for request lifecycle |

### Module 02 — Matching Engine
| Entity | Description |
|--------|-------------|
| ServiceProvider | Provider profile in matching context |
| MatchRound | A single matching execution cycle |
| MatchCandidate | A provider identified as potentially eligible |
| CandidateResponse | Provider's response to being matched |
| CustomerSelection | Customer's choice from presented candidates |
| EligibilityEvaluation | Rule evaluation result for a candidate |
| CandidateRankingScore | Computed ranking for ordering candidates |

### Module 03 — Booking, Assignment & Service Activation Engine
| Entity | Description |
|--------|-------------|
| SelectionLock | Temporary hold during booking confirmation |
| ServiceCase | The overarching case spanning multiple sessions |
| ServiceAssignment | Provider-to-case assignment record |
| AssignmentPlan | Planned schedule for assignments |
| ServiceSession | Individual scheduled session within a case |
| ProviderCommitment | Provider's confirmed commitment |
| CoordinationEvent | Cross-module coordination records |
| ManualHold | Administrative hold on booking progress |

### Module 04 — Service Execution Engine (10 Sub-Engines)
| Entity | Description |
|--------|-------------|
| ServiceSession (Execution) | Active execution context for a service session |
| PresenceRecord | GPS/location verification during execution |
| StartChecklistInstance | Pre-service checklist completion record |
| ExecutionActivity | Individual task/activity during service |
| ObservationRecord | Provider observations during service |
| EvidenceItem | Photos, documents, signatures captured |
| Interaction | Communication between parties during execution |
| Exception | Unexpected issues requiring resolution |
| ExtensionRequest | Request to extend service duration |
| CompletionRecord | Service completion confirmation |
| HandoverRecord | Handover to next session or case closure |

### Module 05 — Financial Operations Engine
| Entity | Description |
|--------|-------------|
| FinancialParty | Any entity with financial identity (customer, provider, org, platform) |
| CommercialContract | Price/terms agreement backing a service case |
| FinancialDocument | Invoice, credit note, debit note, receipt |
| PaymentTransaction | Individual payment attempt/record |
| WalletAccount | Stored-value account for a party |
| EscrowAccount | Held funds pending service completion |
| LedgerEntry | Immutable debit/credit record |
| SettlementBatch | Grouped payouts to providers/organizations |
| FinancialObligation | Pending financial duty (commission, fee) |
| FinancialReservation | Pre-authorized hold on payment |

### Module 06 — Trust, Quality & Governance Engine
| Entity | Description |
|--------|-------------|
| TrustCase | Investigation/governance case |
| Review | Submitted review from a party |
| Rating | Numerical rating associated with a review |
| ReputationProfile | Aggregate reputation score for an actor |
| Evidence (Trust) | Supporting evidence for a trust case |
| CaseDecision | Resolution decision on a trust case |
| EnforcementAction | Action taken (warning, restriction, suspension) |
| Warning | Formal warning issued to an actor |
| Restriction | Limited access/capability imposed |
| Suspension | Full temporary account suspension |
| Appeal | Actor's appeal of an enforcement action |
| ComplianceRecord | Compliance check/verification record |
| RiskSignal | Automated or manual risk indicator |

### Module 07 — Communication Orchestration Engine
| Entity | Description |
|--------|-------------|
| CommunicationSession | End-to-end lifecycle of a communication decision |
| CommunicationRule | Event-to-communication mapping rule |
| CommunicationDeliveryJob | Individual delivery task |
| CommunicationInboxItem | In-app inbox message |
| CommunicationConversation | Threaded conversation context |
| CommunicationReminder | Scheduled reminder |
| CommunicationCampaign | Bulk/scheduled campaign |
| CommunicationTemplate | Versioned message template |
| CommunicationPreference | User channel/category preferences |

### Module 08 — Identity, Roles, Profiles & Access Engine
| Entity | Description |
|--------|-------------|
| Identity | Core identity record |
| Account | Authentication account |
| Credential | Login credentials (password, OAuth, etc.) |
| Actor | Authenticated principal performing actions |
| Organization | Provider-side business entity |
| Department | Sub-unit within an organization |
| Membership | Actor-to-organization relationship |
| RoleAssignment | Role bound to actor within scope |
| Permission | Granular operation permission |
| Profile | Public/private profile data |
| ProfileField | Individual profile attribute |
| VerificationRequest | Identity/document verification request |
| TrustedAccessGrant | Delegated access grant |


### Platform Kernel — Service Supplier Abstraction (Cross-Module)
| Entity | Description |
|--------|-------------|
| ServiceSupplier | Universal abstraction for any entity that can receive, accept, fulfill, or be financially credited for an order. Links to Independent Provider, Organization, or Organization Provider. |
| SupplierCapability | Supplier's declared/verified service capabilities (JSONB, schema-validated) |

> **See Section 16 for complete supplier entity model, lifecycle, and cross-module integration details.**

### Module 09 — Search, Discovery & Filtering Engine
| Entity | Description |
|--------|-------------|
| SearchSession | User's search interaction context |
| SearchQuery | Parsed and normalized query |
| SearchableDocument | Indexed entity for search |
| FacetDefinition | Configurable filter/facet |
| RankingProfile | Configurable ranking algorithm profile |
| SavedSearch | User's saved search criteria |
| IndexOperation | Search index update operation |

### Module 10 — Geospatial, Maps & Location Engine
| Entity | Description |
|--------|-------------|
| LocationPoint | GPS coordinate with metadata |
| StructuredAddress | Parsed address with components |
| ServiceArea | Geographic boundary for service coverage |
| RouteEstimate | Distance/time calculation result |
| GeofenceRule | Area-based trigger rule |
| LiveLocationSession | Real-time location tracking session |
| LocationTrustSignal | Location verification/trust indicator |

### Module 11 — Incentives, Referrals, Promotions & Commission Policy Engine
| Entity | Description |
|--------|-------------|
| Campaign | Marketing/incentive campaign |
| IncentivePolicy | Versioned incentive rule set |
| ReferralRelationship | Referrer-to-referee link |
| Reward | Earned/pending reward record |
| PromotionApplication | Applied promotion instance |
| CommissionAdjustment | Commission override/discount |

### Modules 12–24 — Platform Capability Modules (Shared Entity Pattern)
All modules 12–24 share a common policy-driven entity framework:

| Shared Entity | Description |
|--------|-------------|
| Policy | Versioned business rule container |
| PolicyVersion | Specific version of a policy |
| RuleSet | Collection of rules within a policy |
| EligibilityRule | Condition-based eligibility check |
| DecisionTrace | Audit trail of rule evaluation |
| ActionRequest | Inbound command/request |
| ActionResult | Outcome of processing a request |
| TenantOverride | Tenant-specific configuration override |
| ActorPermissionContext | Permission evaluation context |
| AuditRecord | Module-specific audit entry |
| OperationalLimit | Rate/quota limit definition |
| ProviderBinding | External service provider binding |
| LifecycleState | Entity state machine position |

Additionally, each module defines domain-specific entities through their event catalogs (e.g., Module 19 has FeatureFlag, Experiment, KillSwitch; Module 22 has Job, Schedule, DeadLetter; Module 23 has HealthCheck, Alert, Incident, SLO).


---

## 4. Extracted Dependencies (Module Ownership Map)

### Foundation Layer
```
Module 25 (Platform Kernel) ← ALL modules depend on this
    ├── Shared Identifiers
    ├── CES Event Envelope
    ├── CCS Configuration Envelope
    ├── Shared Error Model
    ├── API Contract Conventions
    ├── Audit Envelope
    ├── Tenant Boundary Standard
    ├── Dependency Governance Rules
    └── ServiceSupplier Abstraction (cross-module entity)
```

### Module Ownership Matrix (from Correction Package)

| Module | Owns | Must Not Own |
|--------|------|--------------|
| 01 Request | Service request intake, draft, submission, approval readiness | Identity, provider ranking, payment, communication delivery |
| 02 Matching | Candidate discovery, ranking, eligibility, matching runs | Assignment finalization, communications, payments |
| 03 Booking/Assignment | Booking confirmation, assignment, activation | Execution records, payment, communication delivery |
| 04 Execution | Service session execution, start, progress, completion, evidence | Financial settlement, trust sanctions, direct communications |
| 05 Financial | Wallet, ledger, invoice, payment, settlement, refund/adjustment | Identity verification, communication delivery |
| 06 Trust/Governance | Reviews, complaints, disputes, risk, enforcement recommendations | Identity source of truth, access engine implementation |
| 07 Communication | Message orchestration, templates, channels, preferences, delivery logs | Business decisions, identity ownership |
| 08 Identity/Access | User, account, actor, role, permission, profile, org membership, verification, access decision | Business workflow ownership |

### Dependency Flow (Corrected)

```
                        ServiceSupplier Abstraction (Kernel)
                                    ↑
                    Used by all modules referencing provider-side actors
                                    ↑
Request (01) → Matching (02) → Booking (03) → Execution (04) → Financial (05)
                                                                      ↓
                                                              Trust/Governance (06)
                                                                      ↓
All Modules → [CES Events] → Communication Orchestration (07) → Communication Delivery (12)
                                                                      
Identity/Access (08) ← All modules (permission evaluation)
                    ← Creates supplier records on profile/org activation

Search (09) ← Indexes from: 01, 02, 03, 04, 08, 11; indexes ServiceSupplier with type facet
Geospatial (10) ← Used by: 01, 02, 03, 04, 09; service areas linked to ServiceSupplier
Incentives (11) ← Consumes from: 01, 03, 04, 05; Produces to: 05; commission by supplier_type
Document/Media (13) ← Used by: 01, 04, 06, 08
Review/Rating (14) ← Consumes from: 04, 06; reviews target ServiceSupplier
CMS/Content (15) ← Platform-wide content
Workflow (16) ← Orchestrates cross-module workflows
Analytics (17) ← Consumes events from all modules
Integration (18) ← External adapters for all modules
Config/Feature Flags (19) ← Used by all modules; owns marketplace.supplier_model config
AI/Recommendation (20) ← Consumes from: 02, 09, 11, 14, 17
Subscription (21) ← Consumed by: 05, 08, 19
Background Jobs (22) ← Used by all modules for async
Observability (23) ← Monitors all modules
i18n/Localization (24) ← Used by all modules for display
```

### Forbidden Dependencies (from Correction Package + Supplier Abstraction)
1. Business modules (01-06) must NOT send communications directly
2. Business modules must NOT duplicate access decisions locally
3. Financial state must NOT drive identity state directly
4. Trust enforcement must be executed through access policies (Module 08), not hidden local flags
5. No circular dependencies between modules
6. No shared mutable database tables across module boundaries
7. No direct imports of another module's internal services
8. **No business module may directly reference Organization or IndependentProvider for order/matching/financial logic — must use ServiceSupplier abstraction**
9. **No `if company:` / `if provider.company:` / `if independent_provider:` conditional logic in business modules**


---

## 5. Extracted Events

### Module 01 — Request Engine Events
- `request.created`, `request.updated`, `request.submitted`, `request.approved`
- `request.rejected`, `request.cancelled`, `request.cancellation_requested`
- `request.published`, `request.expired`, `request.draft_saved`

### Module 02 — Matching Engine Events
- `matching.run.started`, `matching.run.completed`, `matching.run.failed`
- `matching.candidate.generated`, `matching.candidate.filtered`
- `matching.candidate.ranked`, `matching.candidate.presented`
- `matching.response.received`, `matching.response.expired`
- `matching.selection.made`, `matching.recomputed`

### Module 03 — Booking/Assignment Engine Events
- `booking.created`, `booking.confirmed`, `booking.updated`, `booking.cancelled`
- `booking.assignment.created`, `booking.assignment.changed`
- `booking.assignment.accepted`, `booking.assignment.rejected`, `booking.assignment.expired`
- `booking.assignment.removed`, `booking.activation.completed`

### Module 04 — Service Execution Events (58+ events across 10 sub-engines)
**Session Lifecycle:** `session_ready_for_execution`, `provider_en_route`, `provider_arrived`, `arrival_verified`, `session_started`, `session_in_progress`, `session_paused`, `session_resumed`, `session_interrupted`, `session_completed_by_provider`, `customer_confirmation_requested`, `session_completion_confirmed_by_customer`, `session_closed`, `execution_completed`

**Presence/Location:** `provider_presence_verified`, `provider_presence_unverified`, `location_mismatch_detected`, `gps_unavailable_reported`, `unauthorized_departure_reported`

**Activity/Observation/Evidence:** `activity_created`, `activity_completed`, `activity_skipped`, `observation_recorded`, `critical_value_detected`, `evidence_captured`, `evidence_attached`, `evidence_rejected`

**Interaction:** `message_sent`, `message_received`, `issue_reported`, `help_requested`, `communication_escalated`

**Exception:** `exception_created`, `exception_assigned`, `exception_resolved`, `exception_closed`

**Extension:** `extension_requested`, `extension_approved`, `extension_rejected`, `extension_applied_to_session`

**Completion/Handover:** `session_closed`, `session_handed_over`, `service_case_updated`, `next_session_ready`

### Module 05 — Financial Operations Events (50+ events)
**Reservation:** `financial_reservation_created`, `payment_window_started`, `payment_window_expired`, `reservation_released`

**Contract/Pricing:** `offer_price_accepted`, `contract_amount_locked`, `contract_price_correction_requested`

**Financial Document:** `financial_document_drafted`, `financial_document_issued`, `financial_document_approved`, `financial_document_paid`, `financial_document_posted`, `financial_document_closed`

**Payment:** `payment_received`, `payment_failed`, `cash_collection_recorded`, `wallet_debit_recorded`, `payment_transaction_reconciled`

**Wallet:** `wallet_topup_received`, `wallet_order_debit_posted`, `wallet_refund_credit_posted`, `wallet_cashback_credit_posted`, `wallet_withdrawal_requested`, `wallet_withdrawal_completed`

**Escrow:** `escrow_created`, `escrow_funded`, `escrow_release_eligible`, `escrow_allocated`, `escrow_released`, `escrow_refunded`, `escrow_closed`

**Ledger:** `ledger_entry_posted`, `ledger_journal_posted`, `statement_row_created`, `statement_balance_updated`

**Commission:** `platform_commission_calculated`, `organization_commission_calculated`, `provider_payable_allocated`, `financial_obligation_created`

**Refund:** `refund_requested`, `refund_approved`, `refund_rejected`, `reversal_posted`, `credit_note_posted`, `debit_note_posted`

**Settlement:** `net_position_calculated`, `settlement_batch_created`, `settlement_item_completed`, `settlement_item_failed`, `settlement_batch_closed`

**Cross-Module:** `financial_hold_required`, `financial_clearance_granted`, `financial_outcome_published`


### Module 06 — Trust/Governance Events
- `trust.case.opened`, `trust.case.updated`, `trust.case.closed`
- `trust.review.submitted`, `trust.rating.submitted`
- `trust.complaint.created`, `trust.dispute.opened`, `trust.dispute.resolved`
- `trust.enforcement.recommended`, `trust.enforcement.applied`
- `trust.appeal.submitted`, `trust.appeal.approved`, `trust.appeal.rejected`
- `trust.risk_signal.raised`, `trust.restriction.applied`, `trust.suspension.applied`
- `trust.account.restricted`, `trust.account.restored`

### Module 07 — Communication Orchestration Events
**Consumed (from ALL business modules):** RequestCreated, RequestApproved, MatchCreated, MatchAccepted, BookingCreated, BookingConfirmed, BookingCancelled, AssignmentCreated, ServiceStarted, ServiceCompleted, InvoiceCreated, InvoicePaid, ReviewSubmitted, ComplaintCreated, DisputeOpened, UserRegistered, UserVerified, LoginFailed, RoleChanged, OrganizationCreated, PolicyUpdated, MaintenanceScheduled — and 60+ more event types.

**Emitted:** CommunicationEventReceived, CommunicationRuleMatched, CommunicationRuleSkipped, CommunicationSessionCreated, CommunicationSessionCompleted, CommunicationSessionFailed, CommunicationRecipientResolved, CommunicationChannelSelected, CommunicationTemplateRendered, CommunicationJobCreated, CommunicationJobSent, CommunicationJobDelivered, CommunicationJobFailed, CommunicationJobRetryScheduled, CommunicationJobPermanentlyFailed, CommunicationRead, CommunicationEscalated, InboxItemCreated, ReminderScheduled, ReminderTriggered, AnnouncementPublished, CampaignStarted, CampaignCompleted

### Module 08 — Identity/Access Events
- `identity.user.created`, `identity.user.updated`, `identity.user.verified`
- `identity.login.succeeded`, `identity.login.failed`
- `identity.password.changed`, `identity.mfa.enabled`, `identity.mfa.disabled`
- `identity.role_assigned`, `identity.role_removed`, `identity.permission.changed`
- `identity.organization.created`, `identity.organization.approved`, `identity.organization.suspended`
- `identity.membership.added`, `identity.membership.removed`
- `identity.profile.updated`, `identity.verification.completed`

### Module 09 — Search Events
- `search.query.executed`, `search.query.failed`, `search.query.empty_result`
- `search.index.updated`, `search.index.rebuilt`, `search.index.failed`
- `search.saved.created`, `search.saved.executed`
- `search.abuse.detected`, `search.reconciliation.completed`

### Module 10 — Geospatial Events
- `geo.address.created`, `geo.address.validated`, `geo.address.geocoded`
- `geo.service_area.created`, `geo.service_area.updated`
- `geo.route.calculated`, `geo.geofence.triggered`
- `geo.live_session.started`, `geo.live_session.ended`
- `geo.trust_signal.raised`

### Module 11 — Incentives Events (26 emitted, 12 consumed)
- `incentive.campaign.created`, `incentive.campaign.activated`, `incentive.campaign.completed`
- `incentive.referral.created`, `incentive.referral.converted`
- `incentive.reward.earned`, `incentive.reward.paid`
- `incentive.promotion.applied`, `incentive.promotion.expired`
- `incentive.commission.adjustment.created`

### Modules 12–24 — Standard Lifecycle Events Pattern
All modules 12–24 emit a standard set of lifecycle events plus domain-specific events:

**Standard Pattern:** `{module}.policy.created`, `{module}.policy.activated`, `{module}.policy.deprecated`, `{module}.action.requested`, `{module}.action.completed`, `{module}.action.failed`, `{module}.limit.breached`, `{module}.audit.recorded`

**Domain-Specific Highlights:**
- Module 12: NotificationSent, NotificationDelivered, NotificationFailed, NotificationBounced
- Module 16: WorkflowStarted, WorkflowStepCompleted, WorkflowCompleted, WorkflowFailed, EscalationTriggered
- Module 19: FeatureFlagCreated, FeatureFlagEvaluated, ConfigOverridden, ExperimentStarted, KillSwitchActivated
- Module 20: RecommendationGenerated, ModelVersionPublished, PredictionEvaluated, HumanOverrideRecorded
- Module 22: JobScheduled, JobStarted, JobCompleted, JobFailed, DeadLetterCreated
- Module 23: HealthCheckFailed, AlertTriggered, IncidentOpened, IncidentResolved, SloBreached

### Module 25 — Kernel Events
- `Kernel.ContractPublished.v1`, `Kernel.ContractDeprecated.v1`, `Kernel.ContractRetired.v1`
- `Kernel.ConfigurationSchemaPublished.v1`, `Kernel.EventSchemaPublished.v1`
- `Kernel.DependencyViolationDetected.v1`, `Kernel.CompatibilityCheckFailed.v1`
- `Platform.ModuleRegistered.v1`, `Platform.ModuleFrozen.v1`
- `Platform.SharedTypePublished.v1`, `Platform.SharedErrorCodePublished.v1`

### Supplier Abstraction Events (Kernel-level, cross-module)
- `Supplier.Created.v1`, `Supplier.Activated.v1`, `Supplier.Suspended.v1`
- `Supplier.Deactivated.v1`, `Supplier.Restored.v1`
- `Supplier.CapabilityUpdated.v1`, `Supplier.VerificationLevelChanged.v1`
- `Supplier.AvailabilityChanged.v1`
- `Order.SupplierAssigned.v1`, `Order.ExecutionProviderAssigned.v1`
- `Matching.SupplierCandidateGenerated.v1`
- `Financial.SupplierPayableCreated.v1`
- `Review.SupplierReviewed.v1`

> See Section 16.15 for full supplier event specification.

**Total extracted events: ~270+ unique event types across all modules (including supplier abstraction).**


---

## 6. Extracted Configurations

### CCS Naming Standard: `module.group.setting`

### Module 01 — Request Engine Configuration Keys
- `request.creation.requires_customer_identity`
- `request.approval.operator_review_required`
- `request.draft.auto_save_enabled`
- `request.cancellation.requires_approval`
- `request.visibility.future_orders_visible_to_providers`

### Module 02 — Matching Engine Configuration Keys
- `matching.ranking.max_candidates`
- `matching.response.timeout_minutes`
- `matching.fairness.enabled`
- `matching.reranking.enabled`
- `matching.proximity.weight`

### Module 03 — Booking/Assignment Configuration Keys
- `booking.assignment.auto_accept_enabled`
- `booking.lock.ttl_minutes`
- `booking.cancellation.grace_period_minutes`
- `booking.reassignment.enabled`

### Module 04 — Service Execution Configuration Keys
- `execution.presence.gps_required` (per service type, org, risk level)
- `execution.presence.geofence_radius_meters`
- `execution.presence.location_mismatch_policy` (BLOCK_START | ALLOW_WITH_REASON | ALLOW_WITH_CUSTOMER_CONFIRMATION | ALLOW_WITH_ORGANIZATION_APPROVAL | SEND_TO_OPERATIONAL_REVIEW)
- `execution.checklist.templates` (generic, service-type, org, risk-based)
- `execution.evidence.requirement_policy` (REQUIRED | OPTIONAL | CONDITIONAL | NOT_ALLOWED)
- `execution.evidence.retention_duration_days`
- `execution.extension.agreement_timeout_minutes`
- `execution.completion.customer_confirmation_required`

### Module 05 — Financial Operations Configuration Keys
- `financial.wallet.enabled`
- `financial.settlement.hold_days`
- `financial.escrow.enabled`
- `financial.commission.platform_rate`
- `financial.commission.organization_rate`
- `financial.payment.window_hours`
- `financial.refund.auto_approve_threshold`
- `financial.invoice.auto_generation_enabled`

### Module 06 — Trust/Governance Configuration Keys
- `trust.review.enabled`
- `trust.dispute.appeal_allowed`
- `trust.risk.auto_scoring_enabled`
- `trust.enforcement.auto_suspend_threshold`
- `trust.moderation.required_for_reviews`

### Module 07 — Communication Orchestration Configuration Keys (Comprehensive)
**Core:** `communication.enabled`, `communication.event_ingestion.enabled`, `communication.audit.enabled`, `communication.default_locale`, `communication.default_timezone`

**Rules:** `communication.rules.enabled`, `communication.rules.override_mode` (inherit|override|merge|deny_override), `communication.rules.require_approval`, `communication.rules.allow_tenant_override`, `communication.rules.max_active_rules_per_event`

**Channels:** `communication.channels.{sms|email|push|in_app|inbox|dashboard|chat|webhook|voice}.enabled`

**Providers:** `communication.providers.{sms|email|push|voice}.default`, `communication.providers.failover.enabled`, `communication.providers.health_check.enabled`, `communication.providers.credentials.encryption_required`

**Templates:** `communication.templates.versioning.enabled`, `communication.templates.approval_required`, `communication.templates.missing_variable_policy` (fail|skip|render_placeholder|fallback_template), `communication.templates.allow_tenant_templates`

**Preferences:** `communication.preferences.enabled`, `communication.preferences.user_level_enabled`, `communication.consent.marketing_required`, `communication.suppression_lists.enabled`

### Module 08 — Identity/Access Configuration Keys
- `identity.mfa.required_for_critical_actions`
- `identity.provider_affiliation.company_approval_required`
- `identity.password.min_length`
- `identity.session.timeout_minutes`
- `identity.verification.required_documents`

### Module 25 — Kernel Configuration Keys
- `platform.kernel.contract_validation.enabled`
- `platform.kernel.strict_dependency_validation.enabled`
- `platform.kernel.cross_module_write_blocking.enabled`
- `platform.kernel.event_schema_compatibility.mode` (advisory|enforced|migration|emergency)
- `platform.kernel.config_schema_compatibility.mode`
- `platform.kernel.deprecation_warning_days`
- `platform.kernel.freeze_manifest.required`
- `platform.kernel.audit_envelope.required`
- `platform.kernel.tenant_boundary.enforcement_mode`
- `platform.kernel.error_contract.strict_mode`

**Total extracted configuration keys: ~120+ across all modules.**

### Marketplace / Supplier Configuration Keys (Cross-Module, owned by Module 19)
- `marketplace.supplier_model` — enum: `independent_only` | `organization_only` | `hybrid` (tenant-scoped)
- `marketplace.allow_independent_providers` — boolean (tenant-scoped)
- `marketplace.allow_organizations` — boolean (tenant-scoped)
- `marketplace.allow_direct_organization_provider_matching` — boolean (tenant-scoped)
- `marketplace.organization_requires_internal_assignment` — boolean (tenant-scoped)
- `marketplace.independent_provider_self_acceptance_enabled` — boolean (tenant-scoped)
- `marketplace.organization_auto_accepts_orders` — boolean (tenant-scoped)
- `marketplace.organization_provider_direct_payout_enabled` — boolean (tenant-scoped)
- `marketplace.customer_can_choose_supplier_type` — boolean (tenant-scoped)
- `marketplace.search_show_supplier_type_filter` — boolean (tenant-scoped)

> See Section 16.14 for full specification of these keys.

**Updated total extracted configuration keys: ~130+ across all modules (including supplier abstraction).**


---

## 7. Extracted Permissions / Protected Operations

### Permission Naming Standard: `module.resource.action.scope`

### Module 08 Ownership Rule (Binding)
Module 08 owns permission **evaluation**. Every other module only **defines** protected operations. No module may independently decide whether an actor is authorized.

### Module 01 — Request Engine Protected Operations
- `request.draft.create` — Customer, Customer Delegate
- `request.draft.update` — Customer, Customer Delegate (owner)
- `request.submit` — Customer, Customer Delegate (owner)
- `request.approve` — Platform Team Member, Organization Staff (if applicable)
- `request.cancel` — Customer (owner), Platform Team (with reason)
- `request.view` — Owner, assigned providers, platform team
- `request.admin.list_all` — Platform Team Member

### Module 02 — Matching Engine Protected Operations
- `matching.run.trigger` — System Actor, Platform Team
- `matching.candidates.view` — Customer (own request), Platform Team
- `matching.candidate.respond` — Provider (self)
- `matching.selection.make` — Customer (own request)
- `matching.config.update` — Platform Owner

### Module 03 — Booking/Assignment Protected Operations
- `booking.assignment.create` — System Actor (from matching), Platform Team
- `booking.assignment.accept` — Provider (assigned)
- `booking.assignment.reject` — Provider (assigned)
- `booking.cancel` — Customer (owner), Platform Team
- `booking.reassign` — Platform Team, Organization Staff
- `booking.view` — Involved parties, Platform Team

### Module 04 — Execution Protected Operations
- `execution.session.start` — Provider (assigned)
- `execution.session.pause` — Provider (assigned)
- `execution.session.complete` — Provider (assigned)
- `execution.activity.create` — Provider (assigned)
- `execution.evidence.capture` — Provider (assigned)
- `execution.exception.create` — Provider, Customer, Platform Team
- `execution.exception.resolve` — Platform Team, Organization Staff
- `execution.extension.request` — Provider (assigned)
- `execution.extension.approve` — Customer, Platform Team
- `execution.completion.confirm` — Customer
- `execution.location.override` — Platform Team (audited), Organization Staff (audited)

### Module 05 — Financial Protected Operations
- `financial.invoice.issue` — System Actor
- `financial.payment.record` — System Actor, Platform Team
- `financial.refund.request` — Customer, Platform Team
- `financial.refund.approve` — Platform Team, Finance User
- `financial.settlement.trigger` — System Actor, Finance User
- `financial.wallet.topup` — Customer (own)
- `financial.wallet.withdraw` — Provider (own), pending approval
- `financial.ledger.view` — Finance User, Platform Owner
- `financial.admin.adjustment` — Finance User (audited)

### Module 06 — Trust/Governance Protected Operations
- `trust.review.submit` — Customer, Provider (post-completion)
- `trust.complaint.create` — Customer, Provider
- `trust.dispute.open` — Customer, Provider
- `trust.case.assign` — Platform Team, Compliance User
- `trust.case.decide` — Platform Team, Compliance User
- `trust.enforcement.apply` — System Actor (from decision), Platform Team
- `trust.appeal.submit` — Affected party
- `trust.appeal.decide` — Platform Team, Compliance User

### Module 07 — Communication Protected Operations
- `communication.rule.create` — Platform Team
- `communication.rule.update` — Platform Team
- `communication.template.create` — Platform Team
- `communication.template.approve` — Platform Team
- `communication.campaign.create` — Platform Team
- `communication.campaign.send` — Platform Team
- `communication.preference.update` — User (own)

### Module 08 — Identity/Access Protected Operations
- `identity.user.create` — System Actor (registration), Platform Team
- `identity.role.assign` — Platform Owner, Organization Owner (within org)
- `identity.permission.grant` — Platform Owner
- `identity.organization.create` — Provider (self)
- `identity.organization.approve` — Platform Team
- `identity.organization.suspend` — Platform Team, Compliance User
- `identity.profile.update` — User (own)
- `identity.verification.submit` — User (own)
- `identity.verification.approve` — Platform Team

### Required Role Categories (from Correction Package)
1. Platform Owner / Super-Admin
2. Platform Team Member
3. Organization Owner
4. Organization Staff / Admin
5. Organization Operator
6. Independent Provider
7. Organization Provider
8. Customer
9. Customer Delegate
10. Trusted Person
11. Support User
12. Finance User
13. Compliance User
14. Read-Only Auditor

### Supplier Abstraction — Protected Operations (Cross-Module)
- `supplier.view` — Platform Team, Organization Owner (own), Provider (self)
- `supplier.search` — Customer, Platform Team (filtered by marketplace model config)
- `supplier.receive_order` — Active supplier (status=active, matching config permits)
- `supplier.accept_order` — Independent Provider (self), Organization Owner/Staff
- `supplier.assign_execution_provider` — Organization Owner, Organization Staff
- `supplier.update_availability` — Independent Provider (self), Organization Staff (for org)
- `supplier.manage_pricing` — Independent Provider (self), Organization Owner/Staff
- `supplier.receive_payout` — Active supplier (financial clearance)
- `supplier.view_financials` — Independent Provider (own), Organization Owner/Staff (org), Finance User
- `supplier.respond_to_review` — Reviewed supplier (owner)

> See Section 16.13 for full permission context details.


---

## 8. Extracted Policies

All major business rules must be implemented as **versioned policies** with: policy ID, name, version, scope, tenant applicability, effective date range, status, rule payload, validation schema, and audit metadata.

### Identified Policy Domains

| Policy Domain | Owner Module | Description |
|---------------|-------------|-------------|
| Request Approval Policy | 01 | Rules for when requests require operator review |
| Request Cancellation Policy | 01 | Cancellation eligibility, fees, grace periods |
| Matching Ranking Policy | 02 | Weights, factors, fairness rules for provider ranking |
| Matching Eligibility Policy | 02 | Provider eligibility criteria |
| Assignment Acceptance Policy | 03 | Auto-accept rules, timeout, reassignment triggers |
| Booking Cancellation Policy | 03 | Booking-level cancellation rules and penalties |
| Execution Presence Policy | 04 | GPS/location requirements per service type |
| Evidence Requirement Policy | 04 | What evidence is required per context |
| Extension Approval Policy | 04 | Rules for overtime/extension approval |
| Pricing Policy | 05 | Price calculation rules |
| Commission Policy | 05, 11 | Platform/org commission rates and rules |
| Settlement Policy | 05 | Hold periods, payout schedules |
| Refund Policy | 05 | Refund eligibility, auto-approval thresholds |
| Invoice Policy | 05 | Invoice generation, supplemental invoice rules |
| Review Moderation Policy | 06 | Content moderation rules for reviews |
| Trust Scoring Policy | 06 | Risk score calculation rules |
| Enforcement Policy | 06 | Warning/restriction/suspension thresholds |
| Dispute Resolution Policy | 06 | Dispute handling procedures |
| Communication Rule Policy | 07 | Event-to-communication mapping rules |
| Channel Priority Policy | 07 | Channel selection and fallback rules |
| Retry/Escalation Policy | 07 | Retry attempts, escalation triggers |
| Password Policy | 08 | Password strength, rotation rules |
| Session Policy | 08 | Session timeout, concurrent sessions |
| Verification Policy | 08 | Required documents, verification workflow |
| Search Ranking Policy | 09 | Search result ranking factors |
| Geofence Policy | 10 | Geofence rules and triggers |
| Referral Reward Policy | 11 | Referral program rules and rewards |
| Promotion Eligibility Policy | 11 | Promotion application rules |
| Notification Preference Policy | 12 | Default notification preferences |
| Document Retention Policy | 13 | File retention and purge rules |
| Reputation Calculation Policy | 14 | Reputation score algorithm |
| Content Publication Policy | 15 | Content approval workflow |
| Workflow Execution Policy | 16 | Automation rules and escalation |
| Data Retention Policy | 17 | Analytics data lifecycle |
| API Rate Limit Policy | 18 | Rate limiting rules per consumer |
| Feature Flag Rollout Policy | 19 | Gradual rollout rules |
| AI Governance Policy | 20 | Model deployment, safety, override rules |
| Subscription Billing Policy | 21 | Plan, trial, upgrade/downgrade rules |
| Job Retry Policy | 22 | Retry count, backoff, dead-letter rules |
| SLO Policy | 23 | Service level objectives and alerting |
| Locale Fallback Policy | 24 | Language fallback chain |
| **Supplier Assignment Policy** | **03, Kernel** | **Rules for which supplier types can receive orders per marketplace model** |
| **Supplier Matching Policy** | **02, Kernel** | **Which supplier types participate in matching per tenant config** |
| **Supplier Payout Policy** | **05, Kernel** | **Payment routing rules based on supplier type (org vs. independent vs. split)** |
| **Organization Internal Assignment Policy** | **03** | **Whether/when organizations must assign execution providers** |

**Total identified policy domains: 44+**


---

## 9. UI/UX Kernel Plan

### Design System Architecture (Stack-Independent)

The UI/UX Kernel will be implemented as a centralized, tenant-overridable design system regardless of the frontend technology choice (pending Section 2.3 decision).

### Design Token Categories

```
tokens/
├── colors/
│   ├── primary, secondary, accent
│   ├── success, warning, danger, info
│   ├── background, surface, border
│   ├── text, text-muted, text-inverse
│   └── tenant-overridable brand colors
├── typography/
│   ├── font-family (Persian-first: IRANSans/Vazirmatn + fallbacks)
│   ├── font-size scale (12px–48px, 8 steps)
│   ├── font-weight scale
│   └── line-height scale
├── spacing/
│   ├── base unit (4px)
│   └── scale (4, 8, 12, 16, 24, 32, 48, 64, 96)
├── radius/ (0, 2, 4, 8, 12, 16, full)
├── shadows/ (sm, md, lg, xl)
├── z-index/ (dropdown, sticky, modal, toast, tooltip)
├── breakpoints/ (mobile, tablet, desktop, wide)
├── containers/ (sm, md, lg, xl, full)
└── motion/ (duration, easing curves)
```

### Theme System
- Default: Persian RTL theme (dark-mode-ready)
- Tenant branding: logo, favicon, colors, typography, radius, density overridable
- Resolved through Module 19 (Configuration & Feature Flags) as tenant-scoped config
- CSS custom properties for runtime theming

### Required Layout Shells (7)
1. **Public Website** — marketing, service catalog, registration
2. **Customer Portal** — request management, orders, payments, profile
3. **Provider Portal** — assignments, schedule, earnings, profile
4. **Organization/Company Portal** — team management, assignments, billing
5. **Operator/Admin Panel** — day-to-day operations management
6. **Platform Owner/Super-Admin Panel** — full system administration
7. **Auth Pages** — login, register, forgot password, MFA

### Shared Component Library (45+ components)
**Inputs:** Button, TextInput, Select, Checkbox, Radio, Toggle, Textarea, PhoneField, AddressField, JalaliDatePicker, TimePicker, FileUpload, SearchBox, PriceInput

**Display:** Card, Table, Badge, StatusChip, Alert, Toast, Avatar, Rating, PriceDisplay, InvoiceSummary, AuditTimeline, EventTimeline, ProgressBar, Skeleton

**Navigation:** Breadcrumb, Tabs, Pagination, Sidebar, Navbar, Drawer

**Overlay:** Modal, Drawer, Dropdown, Tooltip, Popover, ConfirmDialog

**Layout:** Grid, Stack, Divider, EmptyState, LoadingState, ErrorState

**Composite:** StepperForm, FilterPanel, DataTable (sortable, filterable), MapPicker, LocationPicker, PermissionAwareButton

### RTL Quality Requirements
- All layouts mirror correctly for RTL
- Icons flip where semantically appropriate (arrows, progress)
- Sidebars/drawers open from correct side
- Tables scroll correctly
- Form labels align right
- Mixed Persian/English text renders naturally (BiDi)
- Numbers display in Persian digits where configured


---

## 10. Persian RTL/Jalali Implementation Plan

### Language & Direction
- `<html lang="fa-IR" dir="rtl">`
- All user-facing text in Persian (Farsi)
- API responses in canonical ISO format; localized display added alongside, never instead of

### Calendar Strategy
| Layer | Format | Purpose |
|-------|--------|---------|
| Database | UTC Gregorian (ISO-8601) | Source of truth |
| API Response | ISO-8601 UTC + optional localized field | Interoperability |
| Frontend Display | Jalali/Shamsi | User-facing |
| Frontend Input | Jalali/Shamsi with conversion | User entry |

### Implementation Approach
- **Backend:** Store all timestamps as `DateTimeField` with `timezone.utc`
- **API serialization:** ISO-8601 string + optional `display_date_jalali` field
- **Frontend conversion:** Use `jdatetime` (Python) for server-side when needed, JavaScript library (e.g., `jalali-moment` or `dayjs-jalali`) for client-side
- **Date picker:** Custom Jalali date picker component (part of UI kernel)
- **Validation messages:** All in Persian, served from Module 24 translation catalog

### Digit Display
- Persian digits (۰۱۲۳۴۵۶۷۸۹) for user-facing content where configured
- Configurable via CCS key: `i18n.display.persian_digits_enabled`
- Latin digits preserved in technical contexts (IDs, API responses)

### Currency
- Display format: configurable (Rial vs. Toman) via CCS key
- No hardcoded currency assumption
- Module 24 owns locale-aware formatting rules

### Typography
- Primary font: IRANSans or Vazirmatn (Persian-optimized web font)
- Fallback: system Persian fonts → sans-serif
- Mixed-language support: `font-family` stack handles Latin fallback

### RTL-Specific CSS Strategy
- Use CSS logical properties (`margin-inline-start`, `padding-inline-end`, etc.)
- Flexbox `direction` inherits from document
- Grid layouts use logical placement
- Dedicated RTL testing in acceptance criteria
- Icon mirroring list maintained (arrows, progress indicators)

### Module 24 Ownership
Module 24 (Internationalization & Localization) is the single source of truth for:
- Locale detection and resolution
- Translation string management
- Number/currency formatting
- Date/time formatting
- Calendar system selection
- Plural rules
- Text direction
- Regional compliance rules

No other module should independently decide locale/format behavior.


---

## 11. Confirmed Technology Stack

### Backend (Confirmed)
| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.12+ | Primary language |
| Django | 5.x (target 5.2) | Web framework |
| Django REST Framework | Latest | API layer |
| PostgreSQL | 16+ | Primary database |
| Redis | 7+ | Cache, queues, locks, rate-limiting, transient state |
| Celery | 5.x | Background jobs, scheduled tasks |
| PostGIS | 3.x | Geospatial extension |

### Database Extensions (Confirmed)
- PostGIS (geospatial queries)
- pg_trgm (trigram similarity for search)
- citext (case-insensitive text)
- gen_random_uuid() (UUID generation)
- Full-text search indexes
- JSONB indexes for configuration/policy metadata

### API (Confirmed)
- REST under `/api/v1/`
- JWT authentication
- OpenAPI/Swagger documentation
- Idempotency keys for critical operations

### Frontend (✅ CONFIRMED)
**Django Templates + HTMX/Alpine.js + Tailwind CSS**

| Technology | Version | Purpose |
|-----------|---------|---------|
| Django Templates | (built-in) | Server-side HTML rendering, component includes |
| HTMX | 1.9+ | Server-driven partial updates, progressive enhancement |
| Alpine.js | 3.x | Client-side reactivity, component state |
| Tailwind CSS | 3.4+ | Utility-first styling, RTL plugin, design tokens |
| Tailwind RTL Plugin | Latest | Automatic RTL class generation |
| PostCSS | 8.x | CSS build pipeline for Tailwind |

### Frontend Libraries (Planned)
| Library | Purpose |
|---------|---------|
| `django-tailwind` or manual | Tailwind integration with Django |
| `heroicons` | SVG icon system |
| Custom Jalali picker | Alpine.js-based Jalali date picker component |
| `jalali-moment` or `dayjs-jalali` | Client-side Jalali date formatting |
| `htmx` | Partial page updates without full reload |
| `alpinejs` | Lightweight client-side interactivity |

### Infrastructure (Planned)
| Technology | Purpose |
|-----------|---------|
| Docker | Containerization |
| Docker Compose | Local development |
| GitHub Actions | CI/CD |
| Sentry | Error tracking |
| Prometheus + Grafana | Metrics/monitoring |
| OpenTelemetry | Distributed tracing |

### Python Libraries (Planned)
| Library | Purpose |
|---------|---------|
| `djangorestframework-simplejwt` | JWT auth |
| `django-filter` | API filtering |
| `drf-spectacular` | OpenAPI schema generation |
| `django-redis` | Redis cache backend |
| `celery[redis]` | Task queue |
| `django-celery-beat` | Periodic task scheduling |
| `jdatetime` | Jalali date conversion |
| `django-auditlog` or custom | Audit logging |
| `django-guardian` or custom | Object-level permissions |
| `psycopg[binary]` | PostgreSQL adapter |
| `django-storages` | File storage abstraction |
| `Pillow` | Image processing |


---

## 12. Proposed Database Architecture

### Tenancy Model
- **Approach:** Shared database, shared schema, `tenant_id` column on all tenant-owned tables
- **Enforcement:** Service-layer enforcement (not just frontend filtering)
- **Future option:** PostgreSQL Row-Level Security (RLS) can be layered in later
- **Platform-global tables:** marked explicitly, immutable or centrally governed

### Schema Organization (by Module Boundary)

```
Schema Groups:
├── kernel/          — Tenant, configuration, feature flag, audit, event outbox, SERVICE SUPPLIER
├── identity/        — User, account, role, permission, org, membership, profile
├── request/         — Request, service need, draft, submission
├── matching/        — Match round, candidate, ranking, response, selection
├── booking/         — Service case, assignment, session plan, commitment
├── execution/       — Session, presence, activity, observation, evidence, exception
├── financial/       — Party, contract, document, payment, wallet, escrow, ledger, settlement
├── trust/           — Case, review, rating, reputation, enforcement, appeal
├── communication/   — Rule, session, job, inbox, conversation, template, preference
├── search/          — Index, query, facet, ranking profile, saved search
├── geospatial/      — Address, location, service area, geofence, route
├── incentive/       — Campaign, policy, referral, reward, promotion, commission
├── document/        — File, metadata, version, signature
├── content/         — Article, page, help entry, translation
├── workflow/        — Workflow definition, instance, step, timer
├── analytics/       — Metric, dashboard, report, export
├── integration/     — Endpoint, credential, webhook, log
├── subscription/    — Plan, entitlement, usage, billing
├── scheduler/       — Job, schedule, execution log, dead letter
└── observability/   — Health check, alert, incident, SLO
```

> **Note:** `kernel.service_supplier` is a cross-module entity referenced by matching, assignment, financial, search, and review modules. See Section 16.16 for full DDL.

### Global Identifier Standard (Every Table)
Every entity table must include:
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
tenant_id       UUID NOT NULL REFERENCES kernel.tenant(id)
module_id       VARCHAR(10) NOT NULL  -- e.g., 'M01', 'M05'
entity_type     VARCHAR(100) NOT NULL
external_ref    VARCHAR(255) NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
version         INTEGER NOT NULL DEFAULT 1  -- optimistic concurrency
created_by      UUID NULL REFERENCES identity.actor(id)
updated_by      UUID NULL REFERENCES identity.actor(id)
```

### Key Database Design Principles
1. **No sequential IDs** — UUIDs only (opaque, non-guessable)
2. **Soft delete** via `deleted_at` timestamp + archive strategy
3. **Financial tables are append-only** — ledger entries never mutated
4. **JSONB for flexible schemas** — policy payloads, configuration values, extension metadata (always validated)
5. **Deliberate indexes** — covering indexes for common queries, GIN for JSONB, GiST for PostGIS
6. **Partitioning** — audit logs, events, and analytics by time range
7. **No nullable fields** unless semantically valid (prefer empty defaults)
8. **Optimistic concurrency** via `version` column on all mutable entities

### Event Outbox Pattern
```sql
CREATE TABLE kernel.event_outbox (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    event_type      VARCHAR(200) NOT NULL,
    event_version   VARCHAR(10) NOT NULL,
    payload         JSONB NOT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL,
    published_at    TIMESTAMPTZ NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    retry_count     INTEGER NOT NULL DEFAULT 0,
    correlation_id  UUID NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Estimated Table Count
- Kernel/shared: ~15 tables
- Per business module (01-08): ~8-20 tables each
- Per capability module (09-24): ~5-10 tables each
- **Total estimate: ~250-300 tables**


---

## 13. Implementation Phases

### Phase 0 — Documentation Review & Architecture Intake (THIS DOCUMENT)
- ✅ Review all 25 module documents + Correction Package
- ✅ Produce Architecture Intake Report
- ⏳ Await owner decisions on Section 2 items (Module 7 identity, Module 7/12 boundary, frontend stack)
- Duration: 1 sprint

### Phase 1 — Platform Kernel (Module 25 implementation)
**Scope:**
- Django project scaffold with modular app structure
- Tenant model and tenant-aware base classes
- User model integration (AbstractBaseUser)
- RBAC foundation (permission model, role assignment)
- Audit logging foundation (audit envelope)
- Event outbox and CES publisher
- Configuration foundation (CCS envelope, config resolution)
- Feature flag foundation
- Policy versioning base classes
- **ServiceSupplier abstraction model, resolver service, lifecycle state machine**
- **Marketplace model configuration keys (`marketplace.supplier_model`, etc.)**
- Shared service patterns (base service, base repository)
- Shared API patterns (base viewset, pagination, filtering, error handling)
- Shared UI kernel / design system (tokens, base templates, components)
- Persian RTL base layout
- Jalali frontend integration
- Docker + Docker Compose setup
- Database migrations infrastructure
- **Duration estimate:** 3-4 sprints

### Phase 2 — Identity, Access, and Configuration Foundation
**Scope:**
- Module 08: Full identity system (registration, login, JWT, MFA-ready, profiles, organizations, memberships, roles, permissions, verification)
- **Module 08: Supplier record creation on profile/org activation; supplier RBAC context**
- Module 19: Configuration system (config keys, tenant overrides, feature flags, experiments, kill switches)
- **Module 19: Marketplace supplier model config keys seeded and tenant-configurable**
- Module 24: i18n/Localization (locale resolution, translation catalog, Jalali/Persian formatting, number/currency formatting)
- **Duration estimate:** 3-4 sprints

### Phase 3 — Core Marketplace Transaction Loop
**Scope:**
- Module 01: Request Engine (full lifecycle: draft → submit → approve → publish)
- Module 02: Matching Engine (eligibility, ranking, **supplier-based candidate generation**, response handling; respects `marketplace.supplier_model` config)
- Module 03: Booking/Assignment (**two-level assignment: commercial → supplier, execution → provider**; scheduling, activation)
- Module 04: Service Execution (10 sub-engines: session, presence, checklist, activity, observation, evidence, interaction, exception, extension, completion/handover; resolves execution actor from supplier)
- **Duration estimate:** 5-6 sprints

### Phase 4 — Financial and Trust Layer
**Scope:**
- Module 05: Financial Operations (wallet, ledger, invoice, payment, escrow, **supplier-type-aware commission**, settlement, refund; payable resolved through ServiceSupplier)
- Module 06: Trust/Governance (reviews, ratings, complaints, disputes, risk scoring, enforcement, appeals; **review targets = ServiceSupplier**)
- Module 11: Incentives/Referrals/Promotions/Commission (campaigns, referrals, rewards, promotions; **commission policies per supplier_type**)
- **Duration estimate:** 4-5 sprints

### Phase 5 — Communication, Search, Location, Content
**Scope:**
- Module 07 + 12: Communication (orchestration + delivery — after boundary is documented)
- Module 09: Search/Discovery (indexing, query, facets, ranking)
- Module 10: Geospatial/Maps (address, geocoding, service areas, geofencing)
- Module 13: Document/Media (upload, storage, versioning, scanning)
- Module 14: Review/Rating/Reputation (verified reviews, moderation, reputation scores)
- Module 15: CMS/Knowledge (content management, help center, policy pages)
- **Duration estimate:** 4-5 sprints

### Phase 6 — Automation, Analytics, Integrations, Observability
**Scope:**
- Module 16: Workflow/Automation (event-triggered workflows, approvals, timers)
- Module 17: Analytics/BI (metrics, dashboards, reports)
- Module 18: Integration/API Gateway (external APIs, webhooks, partner integrations)
- Module 20: AI/Recommendation (recommendations, ranking enhancement, predictions)
- Module 21: Subscription/Plans (plan management, billing integration)
- Module 22: Background Jobs/Scheduler (job management, cron, dead-letter)
- Module 23: Observability/Health (health checks, alerts, incidents, SLOs)
- **Duration estimate:** 4-5 sprints

### Phase 7 — Hardening and Final Report
**Scope:**
- Full test suite completion
- **Supplier abstraction test groups (A: independent-only, B: organization-only, C: hybrid) — all must pass**
- Security audit and hardening
- Tenant isolation verification
- Permission matrix verification
- Event consistency review
- Migration completeness review
- UI consistency and RTL review
- Jalali/date handling review
- Performance testing and optimization
- Final technical report
- **Duration estimate:** 2-3 sprints

### MVP Shortcut Path (Phases 0–5)
For an initial sellable MVP: Phases 0–5 deliver a fully functional marketplace end-to-end:
- Signup → Search → Request → Booking → Execution → Payment → Review
- Estimated timeline: 20-25 sprints (~5-6 months with a focused team)


---

## 14. Risks and Missing Information

### High-Priority Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R1 | ~~Module 07/12 boundary unclear~~ | ~~Implementing either module incorrectly~~ | ✅ RESOLVED — Boundary documented in Section 2.2 |
| R2 | ~~Frontend stack undecided~~ | ~~Cannot begin UI implementation~~ | ✅ RESOLVED — Django+HTMX+Tailwind confirmed in Section 2.3 |
| R3 | ~~Module 7 "Business Roles" content status unknown~~ | ~~May be missing critical business rules~~ | ✅ RESOLVED — Merged into Module 08, confirmed in Section 2.1 |
| R4 | Modules 12-24 have templated/generic specs | May need domain-specific entity enrichment before implementation | Flag during implementation; propose extensions per the build prompt protocol |
| R5 | Scale of Module 05 (41 documents) | Extremely complex financial domain; highest defect risk | Dedicated financial domain expertise; extra testing budget |
| R6 | Module 04 complexity (10 sub-engines, 28 docs) | Largest single implementation effort | Break into sub-sprints per engine; frequent integration testing |
| R7 | No payment gateway specified | Cannot implement actual payment processing | Implement provider-abstract adapter pattern; defer real PSP integration |
| R8 | No SMS/Email provider specified | Cannot implement actual communication delivery | Implement provider-abstract adapter; stub providers for development |

### Medium-Priority Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R9 | Cross-module event consistency | Events may drift between modules during parallel development | Enforce CES envelope validation; shared event registry |
| R10 | Multi-tenant testing complexity | Tenant isolation bugs may not surface until production | Dedicated tenant-isolation test suite per module |
| R11 | Persian/Jalali edge cases | Date calculations, leap years, range queries may have subtle bugs | Comprehensive date-handling test suite; use battle-tested libraries |
| R12 | Policy versioning complexity | Versioned policies create complex query patterns | Clear version resolution algorithm; indexed version lookups |
| R13 | Performance at scale | 250+ events, complex matching, full-text search, geospatial | Performance testing from Phase 3; database query optimization |
| R14 | **Supplier abstraction leakage** | Business modules may accidentally bypass supplier abstraction and reference Organization/Provider directly | Code review checklist enforcing supplier pattern; automated lint rule; dedicated tests per marketplace model |
| R15 | **Three-model configuration drift** | Config combinations may create untested edge cases (e.g., hybrid with org auto-accept + independent self-accept) | Combinatorial test matrix for marketplace model configs; document valid combinations |
| R16 | **Two-level assignment complexity** | Commercial vs. execution assignment introduces state management complexity | Clear state machine documentation; explicit assignment_mode enum; dedicated integration tests |

### Missing Information

| Item | Needed For | Blocking? |
|------|-----------|-----------|
| ~~Frontend stack decision~~ | ~~Phase 2 UI implementation~~ | ✅ Resolved |
| ~~Module 7/12 boundary confirmation~~ | ~~Phase 5 communication modules~~ | ✅ Resolved |
| ~~Module 7 "Business Roles" status~~ | ~~Ensuring no missing domain~~ | ✅ Resolved |
| Payment gateway selection (PSP) | Module 05 payment adapter | ❌ No (abstract adapter first) |
| SMS provider selection | Module 12 SMS adapter | ❌ No (abstract adapter first) |
| Email provider selection | Module 12 email adapter | ❌ No (abstract adapter first) |
| Map provider selection | Module 10 map integration | ❌ No (abstract adapter first) |
| Hosting/deployment target | Phase 7 production readiness | ❌ No (Docker-first) |
| Domain name and SSL | Production deployment | ❌ No |
| Persian font license | UI implementation | ❌ No (open-source fonts available) |
| Service taxonomy data | Reference implementation content | ❌ No (structure first, data later) |


---

## 15. Questions Requiring Human Approval

### ~~BLOCKING DECISION 1: Module 07 Identity Conflict~~ — ✅ RESOLVED

**Decision:** Module 07 = Communication Orchestration Engine. "Business Roles & Platform Structure" merged into Module 08. See Section 2.1.

---

### ~~BLOCKING DECISION 2: Module 07 / Module 12 Communication Boundary~~ — ✅ RESOLVED

**Decision:** Module 07 = orchestration/decisioning brain. Module 12 = delivery infrastructure. Business modules emit CES events only. See Section 2.2.

---

### ~~BLOCKING DECISION 3: Frontend Technology Stack~~ — ✅ RESOLVED

**Decision:** Django Templates + HTMX/Alpine.js + Tailwind CSS. Persian-first, RTL, Jalali, server-rendered with progressive enhancement. See Section 2.3.

---

### ✅ All Blocking Decisions Resolved — Implementation May Proceed

All three critical blocking decisions have been answered by the project owner. Phase 1 implementation can now begin.

---

### Additional Confirmations Requested

| # | Question | Default if No Answer |
|---|----------|---------------------|
| Q4 | Is PostgreSQL 16+ acceptable, or is there a specific version requirement? | Use PostgreSQL 16 |
| Q5 | Should the system support multiple tenants from day one, or is single-tenant acceptable for the initial senior-care deployment? | Multi-tenant from day one (per spec) |
| Q6 | Are there existing branding assets (logo, color palette, fonts) for the senior-care reference implementation? | Use sensible defaults, allow override later |
| Q7 | Is there a preferred domain structure for the API? (e.g., `api.domain.com/v1/` vs `domain.com/api/v1/`) | `domain.com/api/v1/` |
| Q8 | For Module 05 (Financial), should we implement a real payment gateway adapter in Phase 4, or is a stub/mock sufficient for MVP? | Stub adapter; real PSP in a later phase |
| Q9 | What is the target deployment environment? (AWS, GCP, Azure, self-hosted, or Docker-only for now?) | Docker-only initially |
| Q10 | Should the initial deployment include both customer-facing and admin portals, or is admin-only acceptable for Phase 1-2? | Both from Phase 2 onward |

---

## 16. Supplier Abstraction and Marketplace Model Variants

> **Status:** Approved architecture requirement. The platform must not be built as only a company-based marketplace or only an independent-provider marketplace. It must support all three models by configuration only — never code changes.

### 16.1 Core Business Requirement

The platform must support these marketplace models by tenant-level configuration:

| Model | Description | Example Verticals |
|-------|-------------|-------------------|
| `independent_only` | No organizations required. Customers request services directly from independent providers. | Freelance tutoring, individual beauty services |
| `organization_only` | No independent providers active. All service delivery through organizations. | Hospital home-care agencies, corporate cleaning companies |
| `hybrid` | Both independent providers and organizations coexist. | General home services, multi-model senior care |

This is domain-neutral. No hard-coded references to nursing, companies, caregivers, technicians, etc.

### 16.2 Service Supplier — The Core Abstraction

**Definition:** A `ServiceSupplier` is the entity that can receive, accept, fulfill, or be financially credited for a service order.

A Service Supplier may be one of:

| Supplier Type | Description |
|---------------|-------------|
| `INDEPENDENT_PROVIDER` | A provider who works directly, not affiliated with an organization |
| `ORGANIZATION` | A company, agency, clinic, studio, contractor group, or any provider-side business entity |
| `ORGANIZATION_PROVIDER` | A provider affiliated with an organization after approval |

**Non-negotiable rule:** The rest of the platform depends on the `ServiceSupplier` abstraction, not directly on `Company`, `Organization`, or `Provider` for any business logic.

### 16.3 Supplier Entity Model

```
ServiceSupplier (Kernel-level cross-module entity)
├── id                    UUID (Global Identifier Standard)
├── tenant_id             UUID NOT NULL
├── supplier_type         ENUM(INDEPENDENT_PROVIDER, ORGANIZATION, ORGANIZATION_PROVIDER)
├── linked_entity_id      UUID NOT NULL
├── linked_entity_type    VARCHAR(100) NOT NULL
├── display_name          VARCHAR(255) NOT NULL
├── status                ENUM(pending, active, suspended, deactivated)
├── capabilities          JSONB (validated, schema-versioned)
├── service_categories    JSONB (linked service taxonomy IDs)
├── availability_status   ENUM(available, busy, offline, on_leave)
├── verification_level    ENUM(unverified, basic, advanced, premium)
├── financial_party_id    UUID NULL (link to Module 05 FinancialParty)
├── reputation_score      DECIMAL NULL (cached from Module 14)
├── metadata              JSONB NULL
├── created_at            TIMESTAMPTZ NOT NULL
├── updated_at            TIMESTAMPTZ NOT NULL
├── version               INTEGER NOT NULL DEFAULT 1
├── created_by            UUID NULL
├── updated_by            UUID NULL
└── module_id             VARCHAR(10) DEFAULT 'M25'
```

Where `linked_entity_type` resolves to:
- `identity.independent_provider_profile` (Module 08)
- `identity.organization` (Module 08)
- `identity.organization_provider_profile` (Module 08)

### 16.4 Supplier Lifecycle State Machine

```
                    ┌─────────────┐
                    │   pending   │
                    └──────┬──────┘
                           │ verify / approve
                           ▼
                    ┌─────────────┐
         ┌─────────│   active    │─────────┐
         │         └──────┬──────┘         │
         │ suspend        │ deactivate     │ capability_update
         ▼                ▼                ▼
  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐
  │  suspended  │  │ deactivated  │  │   active    │
  └──────┬──────┘  └──────────────┘  └─────────────┘
         │ restore
         ▼
  ┌─────────────┐
  │   active    │
  └─────────────┘
```

Transitions are driven by:
- Module 08 (identity verification, organization approval)
- Module 06 (trust enforcement → suspension)
- Module 19 (feature flag / configuration changes)
- Admin operations (platform team)

### 16.5 Supplier Resolution Pattern

Business modules must **never** contain logic like:

```python
# ❌ FORBIDDEN
if company:
    ...
if provider.company:
    ...
if independent_provider:
    ...
```

Instead, business logic depends on supplier capabilities, type, configuration, and policy:

```python
# ✅ REQUIRED PATTERN
supplier = SupplierResolver.resolve(candidate)
AssignmentService.assign_order(order, supplier)
```

The `SupplierResolver` is a kernel-level service that:
1. Accepts a candidate reference (from matching, manual selection, etc.)
2. Resolves it to a `ServiceSupplier` entity
3. Validates supplier status, capabilities, and tenant configuration
4. Returns the supplier abstraction for use by business modules

### 16.6 Order/Request Engine Impact

Orders must be designed independently of supplier type:

```
ServiceCase / Order
├── id
├── tenant_id
├── customer_id
├── service_category_id
├── status
├── supplier_id              UUID NULLABLE → ServiceSupplier
├── execution_provider_id    UUID NULLABLE → Actor (actual person)
├── assignment_mode          ENUM(unassigned, supplier_assigned, execution_assigned)
└── ...
```

Where:
- `supplier_id` = who commercially owns/receives the order
- `execution_provider_id` = actual person performing the service (when applicable)

**Model-specific behavior:**

| Model | supplier_id | execution_provider_id |
|-------|-------------|----------------------|
| Independent Provider | → Independent Provider Supplier | = same provider |
| Organization (direct) | → Organization Supplier | NULL until org assigns |
| Organization Provider | → Organization Supplier | → Org-assigned provider |

### 16.7 Matching Engine Impact

The Matching Engine matches against `ServiceSupplier` candidates:

```
MatchCandidate
├── ...existing fields...
├── supplier_id          UUID → ServiceSupplier
├── supplier_type        ENUM(INDEPENDENT_PROVIDER, ORGANIZATION, ORGANIZATION_PROVIDER)
└── ...
```

Matching policies are configurable per tenant:

| Config Key | Type | Effect |
|-----------|------|--------|
| `matching.allow_independent_providers` | boolean | Include independent providers in match runs |
| `matching.allow_organizations` | boolean | Include organizations in match runs |
| `matching.allow_organization_providers_direct_match` | boolean | Allow org providers to be directly matched (bypassing org acceptance) |

**Resulting behavior:**

| Marketplace Model | Independent Providers | Organizations | Org Providers Direct |
|-------------------|----------------------|---------------|---------------------|
| `independent_only` | ✅ | ❌ | ❌ |
| `organization_only` | ❌ | ✅ | configurable |
| `hybrid` | ✅ | ✅ | configurable |

### 16.8 Assignment Engine Impact — Two-Level Assignment

**Level 1 — Commercial Assignment:**
The order is assigned to a `ServiceSupplier`.

```
Order → Independent Provider Supplier    (independent model)
Order → Organization Supplier            (organization model)
```

**Level 2 — Execution Assignment:**
If the supplier is an organization, the organization may internally assign an execution provider.

```
Order → Organization Supplier → Organization Provider
```

Key rules:
- Do NOT force execution provider assignment at order creation time
- Organizations receive orders first, then assign internally (if policy allows)
- `marketplace.organization_requires_internal_assignment` controls whether execution provider is mandatory before service start

### 16.9 Financial Engine Impact

Financial logic is supplier-based — "pay supplier," not "pay provider":

| Scenario | Payment Flow |
|----------|-------------|
| Independent Provider | Customer → Platform Ledger → Independent Provider payable |
| Organization | Customer → Platform Ledger → Organization payable |
| Organization + Internal Provider | Customer → Platform Ledger → Organization payable (org handles internal compensation) |
| Organization Provider direct payout | Customer → Platform Ledger → Organization payable + Provider payable (policy-driven split) |

Configuration key: `marketplace.organization_provider_direct_payout_enabled`

The system must support future policies where organization providers receive direct payouts, but this is policy-driven, never hard-coded.

### 16.10 Search & Discovery Impact

Search must support filtering by supplier model:

| Filter | Backend Value | Persian Display Label (reference impl) |
|--------|--------------|----------------------------------------|
| Independent providers only | `supplier_type=INDEPENDENT_PROVIDER` | نیروهای آزاد |
| Organizations only | `supplier_type=ORGANIZATION` | شرکت‌ها |
| Both | no filter | همه |

Controlled by: `marketplace.search_show_supplier_type_filter` and `marketplace.customer_can_choose_supplier_type`

### 16.11 Review & Reputation Impact

Reviews support multiple levels:

| Scenario | Review Target(s) |
|----------|-----------------|
| Independent Provider | Supplier review (= provider review) |
| Organization | Supplier review (= organization review) + optional execution provider review |
| Organization Provider | Supplier review (= organization) + execution provider review |

The review system must NOT assume every order has both an organization and a provider.

### 16.12 Notification Impact

Notifications are supplier-aware (resolved by Module 07 Communication Orchestration):

| Supplier Type | Notification Recipient |
|---------------|----------------------|
| Independent Provider | Provider directly |
| Organization | Organization owner/admin/operator (per org notification policy) |
| Organization Provider | Execution provider only when assigned and policy permits |

Business modules emit CES events only. Module 07 resolves recipients using supplier type, permissions, and policy.

### 16.13 Permission / RBAC Impact

Module 08 evaluates access using supplier context. New protected operations:

```
supplier.view
supplier.search
supplier.receive_order
supplier.accept_order
supplier.assign_execution_provider
supplier.update_availability
supplier.manage_pricing
supplier.receive_payout
supplier.view_financials
supplier.respond_to_review
```

Permission contexts:
- Independent Provider acting for self
- Organization Owner acting for organization
- Organization Staff acting within organization scope
- Organization Provider acting within approved organization relationship

### 16.14 Configuration Keys (CCS)

```yaml
# Core marketplace model
marketplace.supplier_model:
  scope: tenant
  owner_module: Module19
  type: enum
  allowed_values: [independent_only, organization_only, hybrid]
  default_value: hybrid

# Supplier type toggles
marketplace.allow_independent_providers:
  scope: tenant
  type: boolean
  default_value: true

marketplace.allow_organizations:
  scope: tenant
  type: boolean
  default_value: true

marketplace.allow_direct_organization_provider_matching:
  scope: tenant
  type: boolean
  default_value: false

# Assignment behavior
marketplace.organization_requires_internal_assignment:
  scope: tenant
  type: boolean
  default_value: false

marketplace.independent_provider_self_acceptance_enabled:
  scope: tenant
  type: boolean
  default_value: true

marketplace.organization_auto_accepts_orders:
  scope: tenant
  type: boolean
  default_value: false

# Financial behavior
marketplace.organization_provider_direct_payout_enabled:
  scope: tenant
  type: boolean
  default_value: false

# UI/Search behavior
marketplace.customer_can_choose_supplier_type:
  scope: tenant
  type: boolean
  default_value: true

marketplace.search_show_supplier_type_filter:
  scope: tenant
  type: boolean
  default_value: true
```

### 16.15 CES Events (Supplier Domain)

New events emitted by the supplier abstraction layer:

```
Supplier.Created.v1
Supplier.Activated.v1
Supplier.Suspended.v1
Supplier.Deactivated.v1
Supplier.Restored.v1
Supplier.CapabilityUpdated.v1
Supplier.VerificationLevelChanged.v1
Supplier.AvailabilityChanged.v1
Order.SupplierAssigned.v1
Order.ExecutionProviderAssigned.v1
Matching.SupplierCandidateGenerated.v1
Financial.SupplierPayableCreated.v1
Review.SupplierReviewed.v1
```

These extend (not replace) existing module event catalogs.

### 16.16 Database Schema Addition

```sql
-- Kernel-level supplier abstraction table
CREATE TABLE kernel.service_supplier (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES kernel.tenant(id),
    module_id               VARCHAR(10) NOT NULL DEFAULT 'M25',
    entity_type             VARCHAR(100) NOT NULL DEFAULT 'ServiceSupplier',
    supplier_type           VARCHAR(30) NOT NULL CHECK (supplier_type IN (
                                'INDEPENDENT_PROVIDER', 'ORGANIZATION', 'ORGANIZATION_PROVIDER'
                            )),
    linked_entity_id        UUID NOT NULL,
    linked_entity_type      VARCHAR(100) NOT NULL,
    display_name            VARCHAR(255) NOT NULL,
    status                  VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN (
                                'pending', 'active', 'suspended', 'deactivated'
                            )),
    capabilities            JSONB NOT NULL DEFAULT '{}',
    service_categories      JSONB NOT NULL DEFAULT '[]',
    availability_status     VARCHAR(20) NOT NULL DEFAULT 'offline' CHECK (availability_status IN (
                                'available', 'busy', 'offline', 'on_leave'
                            )),
    verification_level      VARCHAR(20) NOT NULL DEFAULT 'unverified' CHECK (verification_level IN (
                                'unverified', 'basic', 'advanced', 'premium'
                            )),
    financial_party_id      UUID NULL,
    reputation_score        DECIMAL(5,2) NULL,
    metadata                JSONB NULL,
    external_ref            VARCHAR(255) NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version                 INTEGER NOT NULL DEFAULT 1,
    created_by              UUID NULL,
    updated_by              UUID NULL
);

-- Indexes
CREATE INDEX idx_supplier_tenant ON kernel.service_supplier(tenant_id);
CREATE INDEX idx_supplier_type ON kernel.service_supplier(tenant_id, supplier_type);
CREATE INDEX idx_supplier_status ON kernel.service_supplier(tenant_id, status);
CREATE INDEX idx_supplier_linked ON kernel.service_supplier(linked_entity_id, linked_entity_type);
CREATE INDEX idx_supplier_categories ON kernel.service_supplier USING GIN (service_categories);
CREATE INDEX idx_supplier_capabilities ON kernel.service_supplier USING GIN (capabilities);
```

### 16.17 Cross-Module Integration Map

```
Module 01 (Request)     → References supplier_id on published requests (optional, for targeted requests)
Module 02 (Matching)    → Queries ServiceSupplier for candidates; filters by supplier_type per config
Module 03 (Assignment)  → Assigns order to ServiceSupplier (Level 1) + execution_provider (Level 2)
Module 04 (Execution)   → Resolves execution actor from supplier; presence/evidence linked to execution_provider
Module 05 (Financial)   → Resolves payable party from supplier; commission split by supplier_type
Module 06 (Trust)       → Reviews target ServiceSupplier; reputation aggregated per supplier
Module 07 (Comms)       → Resolves notification recipients from supplier_type + org notification policy
Module 08 (Identity)    → Creates/manages linked entities; supplier record created on profile activation
Module 09 (Search)      → Indexes ServiceSupplier; facets include supplier_type filter
Module 10 (Geo)         → Service areas linked to ServiceSupplier
Module 11 (Incentives)  → Commission policies reference supplier_type
Module 14 (Reviews)     → Review targets are ServiceSupplier entities
```

### 16.18 Required Automated Tests

**Test Group A — Independent-Only Marketplace:**
```
Config: marketplace.supplier_model = independent_only
Assertions:
  ✓ Independent providers can register and be activated as suppliers
  ✓ Organizations are disabled/hidden in UI and matching
  ✓ Matching returns only INDEPENDENT_PROVIDER suppliers
  ✓ Orders assigned to independent provider suppliers
  ✓ Financial payable goes to independent provider
  ✓ Search does not show organization filter
```

**Test Group B — Organization-Only Marketplace:**
```
Config: marketplace.supplier_model = organization_only
Assertions:
  ✓ Independent provider marketplace flow is disabled/hidden
  ✓ Organizations can receive orders as suppliers
  ✓ Organization can internally assign execution provider
  ✓ Matching returns only ORGANIZATION suppliers
  ✓ Financial payable goes to organization
  ✓ Execution provider assignment is optional at booking time
```

**Test Group C — Hybrid Marketplace:**
```
Config: marketplace.supplier_model = hybrid
Assertions:
  ✓ Both independent providers and organizations are available
  ✓ Search can filter by supplier_type
  ✓ Matching can return both supplier types
  ✓ Orders can be assigned to either supplier type
  ✓ Financial payable resolves correctly per supplier_type
  ✓ Reviews target correct supplier entity
  ✓ Notifications route correctly per supplier_type
```

**No supplier-dependent module is complete until all three test groups pass.**

### 16.19 Migration / Implementation Plan

The `ServiceSupplier` abstraction is a **Phase 1 (Platform Kernel) deliverable** because it is a foundational cross-module entity:

| Phase | Supplier-Related Work |
|-------|----------------------|
| Phase 1 | `ServiceSupplier` model, resolver service, base schema, config keys, supplier lifecycle |
| Phase 2 | Module 08 creates supplier records on profile/org activation; supplier RBAC context |
| Phase 3 | Matching queries suppliers; assignment uses two-level model; request references supplier |
| Phase 4 | Financial payable resolves through supplier; commission by supplier_type |
| Phase 5 | Search indexes supplier; reviews target supplier; notifications route by supplier |
| Phase 7 | Full three-model test suite; supplier isolation verification |

### 16.20 Non-Negotiable Design Rules Summary

1. No business module may assume a company/organization always exists
2. No business module may assume an independent provider always exists
3. No business module may assume both exist
4. No `if company:` or `if provider.company:` patterns in business logic
5. Business logic depends on supplier capabilities, type, configuration, and policy
6. Display labels come from the localization/domain mapping layer, never from code
7. All three marketplace models must work without code changes — configuration only
8. The `ServiceSupplier` entity is the universal reference point for orders, matching, assignment, financial, reviews, and notifications

---

## Conclusion

This Architecture Intake Report confirms that all 25 module specifications and the Framework Architecture Correction Package have been thoroughly reviewed. The platform architecture is well-defined, comprehensive, and enterprise-grade.

**The Supplier Abstraction Layer (Section 16) is now an approved, mandatory architectural requirement.** The platform will be built as a configurable supplier-based marketplace supporting `independent_only`, `organization_only`, and `hybrid` models from the beginning.

**Three blocking decisions must still be made before implementation can proceed:**
1. Module 07 identity conflict resolution
2. Module 07/12 communication boundary confirmation
3. Frontend technology stack selection

Once these decisions are confirmed by the project owner, Phase 1 (Platform Kernel) implementation — including the ServiceSupplier abstraction — can begin immediately.

---

*End of Architecture Intake Report v1.0 (Updated with Supplier Abstraction Layer)*
