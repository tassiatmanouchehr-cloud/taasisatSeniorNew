# ADR-001: Enterprise Architecture Freeze v1.0

**Date:** July 6, 2026
**Status:** Accepted
**Author:** Platform Architecture Team
**Applies To:** All implementation phases
**Supersedes:** None

---

## Summary

This ADR records the 24 binding architecture decisions frozen before Phase 1 implementation begins. Every production commit must conform to these decisions. Violations require a new ADR with explicit owner approval.

---

## ADR-001.01 — Person Is Separate from User Account

**Decision:** `Person` and `UserAccount` are distinct entities. A Person is a stable natural-person identity; a UserAccount is an authentication mechanism bound to a Person.

**Status:** Accepted

**Context:** Many platforms conflate "user" with "person," making it impossible to support multiple login methods, account recovery, or multi-role identities without creating duplicates.

**Reason:** A Person may have multiple UserAccounts (phone-based, email-based, OAuth). Identity must survive credential changes. Person.id is permanent; UserAccount is temporal.

**Alternatives Considered:** (A) Single User model with embedded auth — simpler but prevents multi-account and multi-role patterns. (B) Separate Identity service — overkill for current scale.

**Rejected Alternatives:** (A) rejected because it forces one-login-per-person and makes role transitions require account duplication.

**Consequences:** Person table has no auth fields. UserAccount FK → Person. Login flow resolves UserAccount then loads Person context.

**Implementation Impact:** Phase 1 Sprint 1 creates both models. Phase 2 (Module 08) implements full auth flows on top.

**Affected Modules:** M25 (owns Person, UserAccount), M08 (owns Credential, auth flows), All (reference Person.id)

---

## ADR-001.02 — User Is Not Provider

**Decision:** A User (authentication entity) is never directly treated as a Provider (service delivery entity). The path is: Person → Profile → ServiceSupplier.

**Status:** Accepted

**Context:** The platform must support a person being Customer, Provider, Org Owner, and Platform Staff simultaneously without duplicate identities.

**Reason:** If User = Provider, then becoming a Customer requires a second account, or vice versa. The identity model must be role-neutral; roles are temporal memberships.

**Alternatives Considered:** (A) User model with `is_provider` boolean — breaks when person has multiple roles. (B) Separate User and Provider tables with shared email — creates sync nightmares.

**Rejected Alternatives:** Both create identity duplication or role rigidity.

**Consequences:** Business modules never query "User" for provider data. They query ServiceSupplier. Profile entities (IndependentProviderProfile, OrganizationProviderProfile) hold domain-specific data.

**Implementation Impact:** No `provider_id` field on User. No `is_provider` flag. Provider identity exists only through Profile + ServiceSupplier linkage.

**Affected Modules:** M08 (profiles), M25 (ServiceSupplier), M02 (matching), M03 (assignment), M05 (financial)

---

## ADR-001.03 — ServiceSupplier Abstraction Is Mandatory

**Decision:** `ServiceSupplier` is the universal abstraction for any entity that can receive, accept, fulfill, or be financially credited for a service order. All business modules must reference ServiceSupplier, not Organization or Provider directly.

**Status:** Accepted

**Context:** The platform must support independent providers, organizations, and organization providers without business logic branching on entity type.

**Reason:** Without a unified abstraction, every module would need `if company: ... elif provider: ...` conditionals, violating the no-hard-coded-policy principle and making new supplier types impossible without code changes.

**Alternatives Considered:** (A) Polymorphic FK pattern without abstraction — scatters type resolution across all modules. (B) Generic relation using ContentTypes — too implicit, hard to query, no type safety.

**Rejected Alternatives:** (A) rejected because it leaks type-awareness into business modules. (B) rejected because Django ContentTypes add complexity without clear benefit.

**Consequences:** Every order, assignment, matching result, financial payable, review, and notification target references `ServiceSupplier.id`. The SupplierResolver service handles type-aware logic in one place.

**Implementation Impact:** Phase 1 creates ServiceSupplier model. Phase 2 links profiles to suppliers on activation. Phase 3+ uses supplier_id in all business operations.

**Affected Modules:** All business modules (M01-M06, M09, M11, M14)

---

## ADR-001.04 — Supplier Supports Three Marketplace Models

**Decision:** The platform supports `independent_only`, `organization_only`, and `hybrid` marketplace models, switchable by tenant-level configuration without code changes.

**Status:** Accepted

**Context:** Different marketplaces need different provider-side structures. A nursing marketplace may be organization-only; a freelance tutoring platform may be independent-only; a general home services platform needs both.

**Reason:** Hard-coding one model prevents platform reuse across verticals. Configuration-driven supplier models enable white-label deployment for any vertical.

**Alternatives Considered:** (A) Build only hybrid and hide features via UI — leaks complexity. (B) Separate codebases per model — defeats the purpose of a platform.

**Rejected Alternatives:** Both create maintenance burden and prevent true multi-tenant deployment.

**Consequences:** `marketplace.supplier_model` CCS key controls behavior. Matching, search, and visibility engines filter by supplier type per config. Tests must pass for all three models.

**Implementation Impact:** Phase 1 seeds config keys. Phase 3 matching engine respects config. Test groups A/B/C validate all models.

**Affected Modules:** M02, M03, M05, M09, M19 (config owner)

---

## ADR-001.05 — Pricing Engine Separate from Financial Ledger

**Decision:** Price calculation (determining what to charge) is architecturally separate from financial operations (recording payments, posting ledger entries, settling).

**Status:** Accepted

**Context:** Many systems embed pricing logic inside payment modules, making it impossible to preview prices, support dynamic pricing, or change commission rules without touching financial code.

**Reason:** Pricing is a pre-transaction concern (calculate before commit). Financial ops are post-transaction (record after commit). Mixing them violates single responsibility and makes pricing changes risky.

**Alternatives Considered:** (A) Pricing inside Module 05 — simple but couples pricing policy changes to financial code. (B) Pricing as a sub-service of M05 — same coupling, different location.

**Rejected Alternatives:** Both increase financial module complexity and risk when pricing policies change.

**Consequences:** Separate `pricing` PostgreSQL schema. PricePolicy/PriceComponent entities owned by Pricing Engine. M05 receives a PriceCalculation result and processes payment against it.

**Implementation Impact:** Phase 1 defines Pricing aggregate boundary. Phase 4 implements both independently.

**Affected Modules:** Pricing Engine (new), M05 (consumes price calculations), M02 (price-aware matching), M11 (promotions affect pricing)

---

## ADR-001.06 — Capability Engine Separate from Service Category

**Decision:** Capabilities (verified abilities a supplier holds) are architecturally independent from Service Categories (classification hierarchy). A capability can be required by services in multiple categories.

**Status:** Accepted

**Context:** Categories classify services for browsing; capabilities determine eligibility for delivery. A "Medical" category provider may or may not have ICU capability. Categories alone are insufficient for matching.

**Reason:** If capabilities were tied to categories, adding a cross-category capability (e.g., "bilingual service") would require restructuring the category tree. Separation enables orthogonal dimensions.

**Alternatives Considered:** (A) Capabilities as sub-categories — forces tree restructuring for cross-cutting abilities. (B) Tags on providers — no validation, no levels, no expiry.

**Rejected Alternatives:** (A) creates rigid coupling. (B) lacks governance (no verification, no expiry tracking).

**Consequences:** Separate `CapabilityCategory` → `Capability` hierarchy. `CapabilityAssignment` links suppliers to capabilities with level + verification status. Services declare `RequiredCapability`. Matching checks intersection.

**Implementation Impact:** Phase 1 defines entities in domain model. Catalog app implements in Phase 2-3.

**Affected Modules:** Catalog (owns Capability), M25 (owns CapabilityAssignment), M02 (queries for matching)

---

## ADR-001.07 — Availability Is an Independent Subsystem

**Decision:** Availability (schedules, working hours, holidays, leaves, capacity limits) is an independent subsystem, never embedded inside Provider, Organization, or Branch models.

**Status:** Accepted

**Context:** Availability affects matching, booking, and execution. If embedded in provider models, branch-level and org-level availability cannot be managed independently.

**Reason:** Availability composes with any entity (supplier, branch, org). It has its own resolution order (blocks → schedule → capacity → emergency). Embedding it would duplicate logic across entity types.

**Alternatives Considered:** (A) `available_hours` JSON field on Provider — no structure, no inheritance, no branch support. (B) Schedule entity but embedded in M08 — couples identity to scheduling.

**Rejected Alternatives:** (A) is unmanageable at scale. (B) bloats the identity module with scheduling concerns.

**Consequences:** Separate `availability` schema with 8 entities. Polymorphic `owner_type/owner_id` pattern. Resolution order documented. Holiday inheritance (platform → tenant → org → branch → supplier).

**Implementation Impact:** Availability app created in Phase 2-3. Matching (Phase 3) queries availability subsystem.

**Affected Modules:** Availability Engine (new), M02 (matching), M03 (booking), M04 (execution scheduling)

---

## ADR-001.08 — Service Catalog Is More Than Service Category

**Decision:** The service catalog supports a full hierarchy: Category → Service → Package → Option → Variant → Attribute → Unit → Duration → PricingTemplate → RequiredCapability → RequiredDocument → RequiredEquipment → ExecutionRule.

**Status:** Accepted

**Context:** A flat "category → service" model cannot represent bundled packages, configurable options, size variants, or service-specific requirements.

**Reason:** Enterprise marketplaces need rich service definitions. A cleaning service may have options (deep clean, regular), variants (2-hour, 4-hour), and packages (weekly plan). Each may require different capabilities and equipment.

**Alternatives Considered:** (A) Flat category-service model — insufficient for packages, options, variants. (B) JSONB "everything" field — no referential integrity, no querying.

**Rejected Alternatives:** (A) cannot model real marketplaces. (B) is unmanageable and un-queryable.

**Consequences:** Full catalog hierarchy in `catalog` schema. Self-referential categories for nesting. Services declare requirements. Rich filtering in search/discovery.

**Implementation Impact:** Catalog app created in Phase 2-3 with full entity set.

**Affected Modules:** Catalog Engine (new), M01 (request references services), M02 (matching uses requirements), M09 (search indexes catalog)

---

## ADR-001.09 — Organization Hierarchy Is Data-Driven

**Decision:** Organization structure (branches, departments, teams, roles) is entirely data-driven. No hard-coded department names, team structures, or role titles exist in code.

**Status:** Accepted

**Context:** Different organizations have different structures. A hospital has wards; a cleaning company has regions; a tech firm has squads.

**Reason:** Hard-coding structure prevents platform reuse. Each org/tenant must define its own hierarchy via data rows. Roles are `kernel_role` records with `scope_type='organization'`, not Python enums.

**Alternatives Considered:** (A) Fixed department enum — cannot support arbitrary structures. (B) No hierarchy, flat org — insufficient for enterprises.

**Rejected Alternatives:** (A) is too rigid. (B) cannot represent real organizations.

**Consequences:** Organization → Branch → Department → Team are all data entities with N:N cardinality. Custom roles per org/tenant. No code change needed for new org structures.

**Implementation Impact:** M08 (Phase 2) implements full hierarchy as data models.

**Affected Modules:** M08 (owner), M02 (org-aware matching), M03 (org assignment), M05 (org financials)

---

## ADR-001.10 — Branch Model Supported from the Beginning

**Decision:** Organizations may contain multiple branches from day one. Branch is a first-class entity with its own address, service area, providers, schedules, financial settings, and operator team.

**Status:** Accepted

**Context:** Many service organizations operate from multiple locations. Retrofitting branch support later would require schema changes across all modules that reference organizations.

**Reason:** Branch-awareness affects matching (service area), assignment (branch-specific providers), execution (branch schedule), and financials (branch settlement). Adding it later is a breaking change.

**Alternatives Considered:** (A) Single-location org, add branch later — forces migration across all FKs. (B) Branch as a separate org — loses parent-child relationship.

**Rejected Alternatives:** (A) creates expensive migration. (B) loses organizational coherence.

**Consequences:** Branch entity with full independent capabilities. BranchAssignment links people to branches. Configuration resolution: branch → org → tenant → platform.

**Implementation Impact:** M08 (Phase 2) creates Branch model. Matching and assignment respect branch context from Phase 3.

**Affected Modules:** M08, M02, M03, M10 (service areas linked to branches)

---

## ADR-001.11 — Marketplace Visibility and Ranking Are Policy/Config Driven

**Decision:** Which suppliers appear to customers and in what order is determined by configurable VisibilityPolicy (strategy, weights, filters, exclusions), never by hard-coded sorting logic.

**Status:** Accepted

**Context:** Different tenants need different ranking strategies (nearest, highest rated, lowest cost, round robin, AI recommendation). Hard-coding one strategy prevents customization.

**Reason:** Marketplace dynamics change over time. Launch may use "nearest"; maturity may use "AI recommendation." This must be a policy change, not a code deployment.

**Alternatives Considered:** (A) Hard-coded ranking in matching service — cannot customize per tenant. (B) Multiple ranking endpoints — API explosion.

**Rejected Alternatives:** Both create rigidity or complexity.

**Consequences:** 9 configurable strategies in VisibilityPolicy. Ranking weights as JSONB. Per-tenant, per-category, per-region policies. Module 20 (AI) provides rankings for the `ai_recommendation` strategy.

**Implementation Impact:** Phase 3 matching engine implements strategy resolution. VisibilityPolicy seeded per tenant.

**Affected Modules:** M02 (matching), M09 (search), M19 (config), M20 (AI rankings)

---

## ADR-001.12 — Tenant Isolation Is Mandatory

**Decision:** Every business record belongs to exactly one tenant. Cross-tenant access requires explicit platform-level permission and audit classification. `tenant_id` is mandatory on all tenant-owned tables.

**Status:** Accepted

**Context:** The platform is multi-tenant from day one. Data leakage between tenants is a critical security failure.

**Reason:** Shared database with `tenant_id` column is the chosen tenancy model. Service-layer enforcement (TenantAwareModel + middleware) prevents cross-tenant queries by default.

**Alternatives Considered:** (A) Separate database per tenant — operationally expensive at scale. (B) Schema-per-tenant — migration complexity multiplied by tenant count.

**Rejected Alternatives:** (A) and (B) are operationally unsustainable for a SaaS platform with many tenants.

**Consequences:** TenantAwareModel base class enforces `tenant_id`. Middleware resolves tenant per request. Queries auto-filter by tenant. Cross-tenant denied by default (403/404, not data leak).

**Implementation Impact:** Phase 1 Sprint 1 implements Tenant model and TenantAwareModel base.

**Affected Modules:** All modules — every model inherits TenantAwareModel

---

## ADR-001.13 — RBAC Evaluation Belongs to Module 08

**Decision:** Module 08 (Identity, Roles, Profiles & Access) owns permission **evaluation**. Every other module only **defines** protected operations — it must never independently decide whether an actor is authorized.

**Status:** Accepted

**Context:** Distributed authorization decisions lead to inconsistencies. One module might grant access that another would deny. Centralized evaluation ensures consistent access control.

**Reason:** From the Correction Package's Permission_Ownership_Model: "Module 08 owns permission evaluation. Every other module only defines protected operations."

**Alternatives Considered:** (A) Each module evaluates its own permissions — inconsistent, duplicate logic. (B) External auth service — overhead for monolith.

**Rejected Alternatives:** (A) leads to permission drift and security holes.

**Consequences:** Modules publish Protected Operations Catalogs (permission keys). Module 08 evaluates: tenant + role + permission + scope + state + policy + feature-flag. Business modules may reject for domain-state reasons but not authorization reasons.

**Implementation Impact:** Phase 1 creates Permission registry. Phase 2 (M08) implements evaluation engine.

**Affected Modules:** All modules define operations; M08 evaluates; M25 hosts Permission table

---

## ADR-001.14 — Business Modules Emit CES Events Only

**Decision:** Business modules (01-06) must NOT send communications directly. They publish CES (Cross-Module Event System) events. Module 07 orchestrates communication decisions; Module 12 delivers.

**Status:** Accepted

**Context:** From the Correction Package Freeze Gate: "No direct communication delivery outside Module 07. Business modules publish events only."

**Reason:** Direct SMS/email calls from business modules create coupling, inconsistency in templates/channels, and inability to centrally manage communication preferences.

**Alternatives Considered:** (A) Each module sends its own notifications — duplicate template logic, no central consent management. (B) Shared utility library — still couples modules to delivery infrastructure.

**Rejected Alternatives:** Both violate single responsibility and prevent centralized communication governance.

**Consequences:** Business modules write events to EventOutbox. Module 07 consumes events, resolves recipients/channels/templates, creates delivery jobs. Module 12 executes delivery.

**Implementation Impact:** Phase 1 creates EventOutbox. Phase 5 implements Module 07 + 12.

**Affected Modules:** All business modules (producers); M07 (orchestrator); M12 (deliverer)

---

## ADR-001.15 — Configuration Uses CCS

**Decision:** All configurable behavior uses the CCS (Cross-Module Configuration System) with namespaced keys, schema validation, tenant override support, and audit trail.

**Status:** Accepted

**Context:** From Module 25 CCS Kernel Envelope specification. Configuration must be structured, validated, scoped, and auditable.

**Reason:** Ad-hoc settings (Django settings, env vars, database flags) create inconsistency. CCS provides: namespacing, schema validation, scope hierarchy (platform → tenant → org → actor), override policies, and change audit.

**Alternatives Considered:** (A) Django settings file — no per-tenant, no runtime changes. (B) Environment variables — no hierarchy, no validation. (C) Simple key-value table — no schema, no scope resolution.

**Rejected Alternatives:** All lack the governance needed for enterprise configuration.

**Consequences:** ConfigurationKey (definition) + ConfigurationValue (override) in kernel schema. ConfigResolver service with Redis caching. Every configurable behavior references a CCS key.

**Implementation Impact:** Phase 1 Sprint 2 implements config models + resolver. All phases seed their config keys.

**Affected Modules:** All modules (consumers); M19 (lifecycle owner); M25 (contract owner)

---

## ADR-001.16 — Policies Are Versioned

**Decision:** Major business rules (matching, commission, pricing, cancellation, etc.) are implemented as versioned policies with effective dates, immutable version history, and audit metadata.

**Status:** Accepted

**Context:** Business rules change over time. Regulatory requirements demand knowing which rule was in effect when a transaction occurred.

**Reason:** Overwriting policies destroys history. Versioning preserves the rule that was active at any point in time, enabling dispute resolution, compliance audits, and safe rollbacks.

**Alternatives Considered:** (A) Overwrite-in-place with audit log — audit log disconnected from actual rule. (B) Git-versioned config files — not queryable, not tenant-aware.

**Rejected Alternatives:** (A) loses direct linkage between transaction and active rule. (B) is unsuitable for runtime resolution.

**Consequences:** PolicyDefinition → PolicyVersion (1:N). Only one version active at a time. PolicyVersion is immutable after activation. Transactions reference the PolicyVersion.id that was active.

**Implementation Impact:** Phase 1 Sprint 2 implements PolicyDefinition + PolicyVersion base models.

**Affected Modules:** All modules with policies (M01-M06, M11, Pricing, Availability)

---

## ADR-001.17 — No Hard-Coded Business Policy

**Decision:** Anything that may change in the future must be policy-driven, configuration-driven, feature-flag-driven, versioned, tenant-aware, and auditable. Never hard-coded.

**Status:** Accepted

**Context:** From the Master Build Prompt Section 3: commission rules, cancellation rules, matching weights, notification templates, payment timing, pricing rules, role permissions, approval requirements — all must be configurable.

**Reason:** Hard-coding business policy requires code deployment for business changes. A marketplace must allow operators to adjust rules without engineering involvement.

**Alternatives Considered:** None — this is a non-negotiable architectural principle from the project specification.

**Rejected Alternatives:** N/A

**Consequences:** Every business rule is either a CCS configuration key, a versioned policy, or a feature flag. Code contains logic for *how* to apply a policy, never *what* the policy says.

**Implementation Impact:** Pervasive — every module must externalize its rules.

**Affected Modules:** All modules

---

## ADR-001.18 — PostgreSQL Schemas Separated by Domain

**Decision:** Database tables are organized into named PostgreSQL schemas (23 total), not placed in the default `public` schema. Each schema corresponds to a bounded context.

**Status:** Accepted

**Context:** With ~160 entities and 250+ tables, a flat namespace creates name collisions, makes ownership unclear, and complicates backup/archival strategies.

**Reason:** Named schemas provide: namespace isolation, clear ownership, independent backup/restore, schema-level permissions (future), and logical organization matching module boundaries.

**Alternatives Considered:** (A) All tables in `public` with naming conventions — no isolation, name collisions possible. (B) Separate databases per module — cross-module queries impossible without federation.

**Rejected Alternatives:** (A) becomes unmanageable at 250+ tables. (B) eliminates transactional integrity across modules.

**Consequences:** 23 schemas created via initial RunSQL migration. Django models use `db_table = 'schema.table_name'`. Cross-schema FKs are standard PostgreSQL. `search_path` configured in Django connection.

**Implementation Impact:** Phase 1 Sprint 1 Commit 12 creates all schemas.

**Affected Modules:** All modules (each owns tables in its designated schema)

---

## ADR-001.19 — Django Templates + HTMX/Alpine.js + Tailwind CSS

**Decision:** The frontend stack is Django Templates with HTMX for server-driven partial updates, Alpine.js for client-side reactivity, and Tailwind CSS for styling.

**Status:** Accepted

**Context:** Owner decision from Section 2.3 of the Architecture Intake Report. Three options were evaluated; option (b) was selected.

**Reason:** Server-rendered approach matches team capabilities, provides SEO benefits, minimizes JavaScript complexity, enables rapid development, and avoids the overhead of a separate SPA deployment.

**Alternatives Considered:** (A) Vanilla CSS/JS — higher effort for complex UI. (C) Next.js/React SPA — separate deployment, higher complexity, larger team needed.

**Rejected Alternatives:** (A) lacks component framework. (C) is overkill for current phase and team size.

**Consequences:** All UI delivered via Django templates. HTMX handles partial updates (no full page reloads for most interactions). Alpine.js manages client-state (dropdowns, modals, form validation). Tailwind provides design system. No webpack/vite — Tailwind CLI only.

**Implementation Impact:** Phase 1 Sprint 3 implements UI kernel (Tailwind config, base templates, components).

**Affected Modules:** All UI-facing modules share the same template/component system

---

## ADR-001.20 — Persian RTL and Jalali Are Edge/Display Concerns

**Decision:** Backend stores all dates/times as UTC Gregorian (ISO-8601). Persian/Jalali and RTL are display-layer concerns handled at the edge (templates, API response decoration).

**Status:** Accepted

**Context:** The platform is Persian-first but must support future locales. Jalali calendar is for display; Gregorian is for computation and storage.

**Reason:** Jalali dates cannot be used for date arithmetic, range queries, or interoperability. UTC Gregorian is the universal source of truth. Conversion happens at the boundary (input → Gregorian; output → Jalali display).

**Alternatives Considered:** (A) Store Jalali dates in DB — breaks date arithmetic, range queries, timezone handling. (B) Dual storage (both Jalali and Gregorian) — sync risk, wasted space.

**Rejected Alternatives:** (A) creates computation bugs. (B) creates sync issues.

**Consequences:** All `DateTimeField` values are UTC. API responses include ISO-8601 + optional `display_jalali` field. Frontend converts using jdatetime/dayjs-jalali. Date picker inputs Jalali, converts to Gregorian before submission.

**Implementation Impact:** Phase 1 Sprint 3 implements Jalali display utilities. Module 24 (Phase 2) owns locale resolution.

**Affected Modules:** All modules with dates (all); M24 (localization owner)

---

## ADR-001.21 — Financial Ledger Must Be Append-Only

**Decision:** The financial ledger (`LedgerEntry`, `LedgerJournal`) is append-only. Entries are never updated or deleted. Corrections are new entries (reversals, adjustments).

**Status:** Accepted

**Context:** From Module 05 specification and financial accounting standards. A ledger that allows mutations cannot be audited or reconciled.

**Reason:** Immutable ledger provides: complete audit trail, reconciliation integrity, regulatory compliance, dispute resolution capability, and forensic analysis support.

**Alternatives Considered:** (A) Mutable balance table with transaction log — balance can drift from log. (B) Soft-delete on ledger entries — violates accounting principles.

**Rejected Alternatives:** (A) creates reconciliation risk. (B) violates financial audit requirements.

**Consequences:** No UPDATE/DELETE on ledger tables. Corrections via debit/credit reversal entries. Balance is always computable from entry sum. Partitioning by time for performance.

**Implementation Impact:** Phase 4 (M05) implements immutable ledger models with append-only constraint.

**Affected Modules:** M05 (owner), M11 (commission entries), M17 (analytics reads)

---

## ADR-001.22 — Communication Boundary: Module 07 Orchestrates, Module 12 Delivers

**Decision:** Module 07 (Communication Orchestration) decides who/when/what/which-channel. Module 12 (Communication & Notification) owns delivery infrastructure (provider adapters, sending, status, retries).

**Status:** Accepted

**Context:** Owner decision from Section 2.2 of the Architecture Intake Report. Two modules overlap in "communication" scope; their boundary was explicitly documented and approved.

**Reason:** Separating decision-making from execution enables: independent scaling, provider substitution without orchestration changes, centralized consent/preference management, and clear failure domain isolation.

**Alternatives Considered:** (A) Single communication module — too large, mixes concerns. (B) Module 07 does everything, Module 12 is only provider adapters — Module 12 becomes too thin.

**Rejected Alternatives:** (A) is too monolithic. The approved boundary is the correct balance.

**Consequences:** Business modules → CES events → M07 (decides) → delivery contract → M12 (sends). M07 owns rules, templates, preferences, inbox. M12 owns adapters, delivery attempts, status tracking.

**Implementation Impact:** Phase 5 implements both modules with clear contract between them.

**Affected Modules:** M07 (orchestration), M12 (delivery), All business modules (event producers)

---

## ADR-001.23 — Production Code Must Follow the Frozen Domain Model

**Decision:** All production code (models, services, APIs) must conform to the entity definitions, aggregate boundaries, cardinality relationships, and lifecycle state machines documented in Phase 0.5 Enterprise Domain Model Freeze.

**Status:** Accepted

**Context:** The domain model was frozen explicitly to prevent ad-hoc schema decisions during implementation that would require future redesigns.

**Reason:** Enterprise systems fail when implementation diverges from design. The frozen model ensures consistency across all phases, all developers, and all modules.

**Alternatives Considered:** (A) Flexible model that evolves during implementation — leads to inconsistency and rework. (B) No freeze, iterate — acceptable for startups but not enterprise platforms.

**Rejected Alternatives:** (A) creates technical debt. (B) is inappropriate for this project's scale.

**Consequences:** Any deviation from the frozen model requires a new ADR with owner approval. Model entity names, relationships, and lifecycles are binding. Implementation may add internal details (indexes, caching) but not change the domain structure.

**Implementation Impact:** Every phase, every sprint, every commit is validated against the frozen model.

**Affected Modules:** All modules

---

## ADR-001.24 — Supplier-Based Matching, Assignment, Financial, Review, Notification, Reporting

**Decision:** Matching, assignment, financial payable, review targets, notification routing, and reporting all reference ServiceSupplier as their primary supply-side entity. No module may bypass this abstraction.

**Status:** Accepted

**Context:** This is the operational consequence of ADR-001.03 (ServiceSupplier mandatory) applied to all downstream modules.

**Reason:** If any module references Organization or Provider directly for business operations, the supplier abstraction breaks and marketplace model switching becomes impossible.

**Alternatives Considered:** None — this is a non-negotiable corollary of the supplier abstraction decision.

**Rejected Alternatives:** N/A

**Consequences:**
- Matching: candidates are ServiceSupplier records
- Assignment: `service_assignment.supplier_id` → ServiceSupplier
- Financial: payable party resolved through ServiceSupplier → FinancialParty
- Reviews: `review.target_id` → ServiceSupplier
- Notifications: recipient resolution uses supplier_type + org policy
- Reporting: supplier-type dimension available on all reports

**Implementation Impact:** Enforced from Phase 3 onward. Phase 1 creates the ServiceSupplier model that all later modules depend on.

**Affected Modules:** M02, M03, M04, M05, M06, M07, M09, M11, M14, M17

---

*End of ADR-001*
