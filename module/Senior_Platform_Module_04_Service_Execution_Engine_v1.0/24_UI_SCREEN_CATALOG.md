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

# 24 — UI Screen Catalog

## Provider Screens

### 1. Session Start Screen
En-route button, arrival button, GPS status, distance-to-target indicator.

### 2. Start Checklist Screen
Dynamic checklist items (boolean, text, number, photo, signature, GPS confirmation, file, single/multi-select, domain form fields).

### 3. In-Session Screen
Add activity, add note/observation, add evidence, request support, report issue, request extension, request temporary leave, complete session.

### 4. Completion Screen
Completion note, final checklist, final evidence, submit for customer confirmation.

## Customer Screens

### 5. Live Session Status Screen
Session status (en route / arrived / in progress / completed / confirmed), provider info, live updates.

### 6. Completion Confirmation Screen
Confirm completion, give feedback, rate service, report dispute.

### 7. Extension Request / Response Screen
View counterpart's extension request; approve or reject; see price-impact status.

## Organization Screens

### 8. Organization Execution Dashboard
Today's sessions, providers en route, problem cases, open exceptions.

### 9. Exception Management Screen
List, assign, and resolve exceptions by severity and status.

### 10. Extension Operational Review Screen
Unresolved/disputed extensions requiring Organization intervention.

## Platform Team (Platform Owner) Screens

### 11. Platform Execution Dashboard
Crises, critical exceptions, disputed completions, unresolved extensions across the platform.

### 12. Session Admin Detail
Full session state, all sub-engine records, audit trail, manual override controls.

### 13. Execution Settings Panel
GPS requirement, distance radius, evidence requirements by phase, checklist templates, extension timeout — configurable by Core / Organization / Service Type / Session scope.

## Explicitly Deferred UI

- A dedicated legal/crisis exception UI is deferred pending legal review, consistent with the module's explicitly deferred scope.
