# Generic Service Marketplace Framework

**Module 04 — Service Execution & Session Lifecycle Engine**

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Frozen |
| **Document Owner** | Product Architecture |
| **Project** | Generic Service Marketplace Framework Reference Implementation (reference implementation of the Generic Service Marketplace Framework) |
| **Module Owner** | Platform Owner |
| **Depends On** | Module 01 — Request Engine, Module 02 — Matching Engine, Module 03 — Booking, Assignment & Service Activation Engine |
| **Next Modules** | Module 05/06 — Payment & Settlement, future Quality / Dispute / Reporting modules |
| **Language** | Persian business domain, English technical structure |

> Modules 01–03 are Frozen and Approved and are treated as baseline. Module 04 must not change their decisions unless a major architectural conflict is discovered.

> **Architecture Upgrade Notice:** starting with this module, the project is no longer designed as a single-purpose reference implementation platform. It is designed as a **Generic Service Marketplace Framework** (Layer 1 — Core Platform, domain-independent) with **Generic Service Marketplace Framework Reference Implementation as its first reference implementation** (Layer 2 — reference implementation Domain Mapping). Every section below states the Core Platform pattern first, then its reference implementation mapping.

# 00 — README

## Package Contents

This documentation package contains the standard Module 04 output for the Generic Service Marketplace Framework Reference Implementation platform: **Service Execution & Session Lifecycle Engine**. This is the first module designed under the project's new two-layer architecture (Generic Core Platform + reference implementation Domain Mapping).

### Documents

1. `01_EXECUTIVE_SUMMARY.md`
2. `02_PLATFORM_ARCHITECTURAL_PRINCIPLES.md` — the project's architecture "constitution," applying to Module 01+ and all future modules
3. `03_PRODUCT_SPECIFICATION.md`
4. `04_BUSINESS_RULES.md`
5. `05_ARCHITECTURE.md`
6. `06_DOMAIN_MODEL.md`
7. `07_STATE_MACHINES.md`
8. `08_FLOWS.md`
9. `09_SESSION_LIFECYCLE_ENGINE.md` (Primary)
10. `10_PRESENCE_LOCATION_ENGINE.md` (Supporting)
11. `11_START_CHECKLIST_ENGINE.md` (Supporting)
12. `12_ACTIVITY_ENGINE.md` (Primary)
13. `13_OBSERVATION_ENGINE.md` (Supporting)
14. `14_EVIDENCE_ENGINE.md` (Supporting)
15. `15_INTERACTION_ENGINE.md` (Primary)
16. `16_EXCEPTION_RESOLUTION_ENGINE.md` (Primary)
17. `17_EXTENSION_OVERTIME_ENGINE.md` (Supporting)
18. `18_COMPLETION_HANDOVER_ENGINE.md` (Primary)
19. `19_EVENT_CATALOG.md`
20. `20_NOTIFICATION_ENGINE.md`
21. `21_DATA_MODEL.md`
22. `22_API_CONTRACT.md`
23. `23_PERMISSION_MATRIX.md`
24. `24_UI_SCREEN_CATALOG.md`
25. `25_ADMIN_CONFIGURATION.md`
26. `26_TEST_SCENARIOS.md`
27. `27_PRODUCT_BIBLE_UPDATE.md`
28. `28_ADR.md`
29. `VERSION.md`
30. `CHANGELOG.md`

## Frozen Scope (Start Boundary)

Module 04 starts exactly where Module 03 ends: the instant the provider taps **"Start Service"** on a scheduled Service Session (Decision 03-051, Module 03).

## Frozen Scope (End Boundary)

Module 04 ends when a Service Session is formally **Closed and Handed Over** — i.e. Execution is complete, Customer confirmation (or Operational Review resolution) is recorded, and the Service Case has been updated. Module 04 produces only **events**; it never produces invoices, settlements, or payouts (ADR-04-012, BR-04-081).

```text
Module 03 → Service Started
        ↓
Module 04 (this module) → Session Closed & Handed Over (events only)
        ↓
Module 05/06 — Payment & Settlement (future)
```

## Ten Sub-Engines

Module 04 is deliberately decomposed into ten sub-engines rather than documented as one monolithic workflow — the same decomposition approach that gave Modules 01–03 reusable, coherent architecture.

**Primary Engines** (independent entity, own lifecycle):
- Session Lifecycle Engine
- Execution Activity Engine
- Interaction Engine
- Exception & Resolution Engine
- Completion & Handover Engine

**Supporting Engines** (serve the primary engines, individually removable per implementation):
- Presence & Location Engine
- Start Checklist Engine
- Observation & Notes Engine
- Evidence Engine
- Extension & Overtime Engine

## Explicitly Deferred (Open Issues)

The following remain intentionally outside this module's architecture, exactly as agreed in Discovery:

- Death, serious accidents, insurance, force majeure, legal liability, and complex legal exception scenarios — deferred to future modules after legal review.
- Evidence retention "legal hold" — deferred to a future module.
- All financial logic (invoicing, settlement, payout) — Module 04 only emits events for future financial modules.

## Freeze Conditions Met

1. **Business Complete** — all ten sub-engines, their lifecycles, and business rules are defined.
2. **Edge Cases Complete (structural)** — exception categories, severities, and independent exception lifecycle are defined; legally sensitive crisis scenarios remain explicitly deferred.
3. **Enterprise Ready** — event-driven, immutable-record, fully audited design; Primary/Supporting engine classification clarifies dependency boundaries for future scaling.
4. **Future Ready** — the module is explicitly designed as a reusable Core Platform pattern set with a reference implementation mapping layer, so it is directly reusable for future marketplace implementations (beauty, cleaning, tutoring, home repair, etc.) without redesign.


---

# Generic Framework Correction Notice
This package has been corrected to operate as a generic, reusable, event-driven service marketplace module. Domain-specific terminology, where retained, is non-normative reference implementation material only.
