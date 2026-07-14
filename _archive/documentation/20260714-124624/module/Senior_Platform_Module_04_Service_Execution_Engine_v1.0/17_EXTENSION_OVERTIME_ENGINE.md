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

# 17 — Extension & Overtime Engine (Supporting)

## Purpose
Manage requests to extend a Session's duration, ensuring every extension is explicit about who requested it, why, how long, whether both sides agree, whether there's a cost impact, and what happens if they don't agree.

## Business Goal
Prevent silent, undocumented overtime — every minute added to a session must be traceable to an agreement or an operational decision.

## Functional Specification

### Core Concepts
Extension Request, Overtime Request, Mutual Agreement, Price Agreement, Disagreement, Operational Review, Extension Decision, Extension Record.

### Extension Lifecycle
```text
REQUESTED → WAITING_COUNTERPART_APPROVAL → APPROVED → APPLIED → CLOSED
```
Exception states: REJECTED, DISPUTED, EXPIRED, CANCELLED, OPERATIONAL_REVIEW_REQUIRED.

## Business Rules
BR-04-069 through BR-04-075 (see `04_BUSINESS_RULES.md`). The central rule is **BR-04-070**: an extension is only valid with **mutual agreement** between Customer and Provider; absent agreement, Organization or Platform Team must intervene (ADR-04-011).

## reference implementation Implementation
Family requests the provider stay an extra hour; provider says the service activity isn't finished yet; family and provider agree on the extra time; they disagree on the extra cost; the company or Platform Owner's team calls; the planned Service Session time is updated accordingly.

## Non-Functional Requirements
- An approved Extension must propagate to the Session's expected end time, planned duration, timeline, and event log (BR-04-074) — never silently tracked outside the session record.

## Edge Cases (structural, non-legal)
- Extension requested but the counterpart never responds — must move to EXPIRED rather than remaining WAITING_COUNTERPART_APPROVAL indefinitely.
- Price impact disputed even though the time extension itself is agreed — the time extension can still be APPLIED while the price dispute routes separately to Operational Review, since financial resolution is out of Module 04's scope entirely (BR-04-075).

## Future Extension
- Automated price-impact calculation, once financial modules exist (explicitly out of scope for Module 04).

## Open Questions
- None explicitly raised beyond financial-calculation deferral.

## Related ADR
ADR-04-011 (see `28_ADR.md`)

## Related Domain Objects
ExtensionRequest, ServiceSession, Interaction
