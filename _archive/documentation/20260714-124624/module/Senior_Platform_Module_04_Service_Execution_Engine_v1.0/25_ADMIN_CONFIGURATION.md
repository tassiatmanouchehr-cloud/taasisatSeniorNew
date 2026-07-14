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

# 25 — Admin Configuration

## Platform Team (Platform Owner) Functions

### Configuration
- GPS mandatory/optional per Service Type, Organization, Request, Session Risk Level, Customer Preference (BR-04-011)
- Distance/geofence radius (reference implementation default 100–300m)
- Location mismatch behavior policy (BLOCK_START / ALLOW_WITH_REASON / ALLOW_WITH_CUSTOMER_CONFIRMATION / ALLOW_WITH_ORGANIZATION_APPROVAL / SEND_TO_OPERATIONAL_REVIEW)
- Start checklist templates (generic, service-type, organization, request-specific, risk-based, domain-specific)
- Evidence requirement rules (REQUIRED / OPTIONAL / CONDITIONAL / NOT_ALLOWED) by Service Type, Organization, Request, Session, Risk Level, and phase
- Evidence retention duration (30/90/180 days, 1 year, custom)
- Notification recipients/templates/channels per event
- Extension agreement timeout

### Operational Control
- View all sessions and their live status
- View, assign, and resolve Exceptions
- Manually override location validation (audited)
- Manually resolve disputed completions and extensions
- View full audit trail per session

## Organization Functions

Subject to permission:
- View own providers' sessions and dashboards
- Assign/claim and resolve Exceptions for own sessions
- Override location validation for own providers (audited)
- Resolve extension disagreements via Operational Review
- Call customers when confirmation fails

## Forbidden Admin Behavior

- Editing or deleting any execution record (activity, observation, evidence, presence, interaction) — only Review/Correction/Note/Dispute/Verification/Audit may be appended (ADR-04-001)
- Revealing real phone numbers between Customer and Provider (ADR-04-008)
- Closing a session without customer confirmation or Operational Review resolution (BR-04-006, BR-04-007)
- Silently resolving an Exception without a recorded resolution (BR-04-063)
- Generating financial output of any kind (BR-04-010, BR-04-081)

## Audit Requirements

Every manual action must record: actor, role, timestamp, session/entity, action, reason, previous state, new state, trigger, related event — per Platform Principle 18 (Audit by Design).
