# Generic Service Marketplace Framework

**Module 03 — Booking, Assignment & Service Activation Engine**

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Frozen |
| **Document Owner** | Product Architecture |
| **Project** | Generic Service Marketplace Framework Reference Implementation |
| **Module Owner** | Platform Owner |
| **Depends On** | Module 01 — Request Engine, Module 02 — Matching Engine |
| **Next Modules** | Module 04 — Service Execution / Care Delivery Engine, Module 05/06 — Payment & Settlement |
| **Language** | Persian business domain, English technical structure |

> Module 01 and Module 02 are Frozen and Approved and are treated as baseline. Module 03 must not change their decisions unless a major architectural conflict is discovered.

# 00 — README

## Package Contents

This documentation package contains the standard Module 03 output for the Generic Service Marketplace Framework Reference Implementation platform: **Booking, Assignment & Service Activation Engine** (ماژول ۰۳ — موتور رزرو، تخصیص نهایی و فعال‌سازی خدمت).

Starting with Module 03, the project upgrades its documentation standard: every file carries its own header (with Depends On / Next Modules), and every major section follows a fixed template — Purpose, Business Goal, Functional Specification, Business Rules, Non-Functional Requirements, Edge Cases, Future Extension, Open Questions, Related ADR, Related Domain Objects — so each file is independently usable by a human, a developer, or a coding agent.

### Documents

1. `01_EXECUTIVE_SUMMARY.md`
2. `02_PRODUCT_SPECIFICATION.md`
3. `03_BUSINESS_RULES.md`
4. `04_ARCHITECTURE.md`
5. `05_DOMAIN_MODEL.md`
6. `06_STATE_MACHINES.md`
7. `07_FLOWS.md`
8. `08_SERVICE_CASE.md`
9. `09_SERVICE_ASSIGNMENT.md`
10. `10_SERVICE_SESSION.md`
11. `11_EVENT_ENGINE.md`
12. `12_NOTIFICATION_ENGINE.md`
13. `13_DATA_MODEL.md`
14. `14_API_CONTRACT.md`
15. `15_PERMISSION_MATRIX.md`
16. `16_UI_SCREEN_CATALOG.md`
17. `17_ADMIN_CONFIGURATION.md`
18. `18_TEST_SCENARIOS.md`
19. `19_PRODUCT_BIBLE_UPDATE.md`
20. `20_ADR.md`
21. `VERSION.md`
22. `CHANGELOG.md`

## Frozen Scope (Start Boundary)

Module 03 starts exactly where Module 02 ends: with a **Customer Selected Candidate / Selection Lock** — the customer/family has chosen one option (for a service need or a package) and that choice is temporarily locked.

Module 03 answers one question: *after the customer/family chooses an option, how does the system turn that choice into a reliable, trackable executive commitment?*

```text
Selection → Final Confirmation → Booking/Assignment → Coordination → Pre-Service Readiness → Service Activation
```

## Frozen Scope (End Boundary)

**Decision 03-051 — Module 03 ends exactly when the "Service Started" event is recorded** (the provider taps "Start Service" after arriving and entering the home). Everything from request creation through matching, selection, service case creation, session scheduling, coordination, en-route, and arrival belongs to Module 03. Everything from the moment care actually begins belongs to Module 04.

This boundary was chosen deliberately over ending earlier (e.g. at "Ready to Start"), because ending earlier would push arrival, delay, and no-show handling into Module 04 before any service has actually happened — which is not logically part of care delivery.

## In Scope

- Selection Lock Management
- Final Confirmation Flow (customer side and provider side)
- Provider Commitment (independent provider, company provider, company package — three distinct paths)
- Assignment Creation (Service Assignment, including multi-need Assignment Plans)
- Booking State Machine
- Pre-Service Coordination (en route, arrival, delay handling)
- Failure & Recovery (rejection, non-response, withdrawal, replacement, conflicts, lock expiry)
- Role Dashboards (customer, provider, company, Platform Owner)
- Audit & Traceability

## Out of Scope

- **Payment / Settlement** — fees, wallet, invoicing (Module 05/06)
- **Care Delivery Execution** — daily reports, vitals, care checklists (Module 04)
- **Matching / Ranking / Eligibility** — already locked in Module 02
- **Request Intake / Service Need creation** — already locked in Module 01
- **Provider Onboarding** — registration and document review is part of Provider Lifecycle, not Module 03

## Explicitly Deferred (Open Issues)

Two topics were intentionally **not** designed in this Discovery round and are carried forward as open issues rather than invented here:

1. **The ~100-item crisis/legal Exception Scenario library** (internet loss, GPS off, phone off, customer death, provider accident, wrong address, hospitalization, etc.). The product owner explicitly postponed this, since it requires legal consultation before being encoded as business rules. Section 18 (Test Scenarios) and Section 03 (Business Rules) therefore cover only the **structural** failure/recovery cases that were already decided in scope (rejection, non-response, withdrawal, replacement, lock expiry, conflicting selection) — not the legally sensitive crisis scenarios.
2. **Public marketing "showcase" / landing page design** — raised briefly in the conversation but not part of Module 03's product architecture; belongs to a separate front-of-site design track.

## Freeze Conditions Met

1. **Business Complete** — booking, confirmation, commitment, assignment, and coordination rules defined for all three provider paths.
2. **Edge Cases Complete (structural)** — rejection, late response, withdrawal, replacement, conflict, and lock-expiry scenarios designed; legal/crisis scenarios explicitly deferred (see Open Issues).
3. **Enterprise Ready** — event-driven, auditable, dashboard-aware design.
4. **Future Ready** — reserved extension points for GPS-based coordination, auto-escalation, and AI-assisted dispatch.


---

# Generic Framework Correction Notice
This package has been corrected to operate as a generic, reusable, event-driven service marketplace module. Domain-specific terminology, where retained, is non-normative reference implementation material only.
