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

# 16 — Exception & Resolution Engine (Primary)

> Deliberately renamed during Discovery from "Exception & Escalation Engine" to "Exception & Resolution Engine" — because the goal is not just raising an issue (escalation is only one tool), the goal is resolving it.

## Purpose
Detect, record, classify, track, resolve, and record the outcome of anything that disrupts normal Session execution.

## Business Goal
Ensure that no operational problem is ever silently lost — every disruption becomes a trackable, ownable, resolvable record, reusable later for complaints, quality issues, and disputes.

## Functional Specification

### Exception Categories
START_EXCEPTION, EXECUTION_EXCEPTION, COMMUNICATION_EXCEPTION, CUSTOMER_EXCEPTION, PROVIDER_EXCEPTION, LOCATION_EXCEPTION, SAFETY_EXCEPTION, TECHNICAL_EXCEPTION, CONFIGURATION_EXCEPTION, CUSTOM_EXCEPTION.

### Severity
LOW, MEDIUM, HIGH, CRITICAL.

### Status
OPEN, UNDER_REVIEW, WAITING_INFORMATION, WAITING_CUSTOMER, WAITING_PROVIDER, WAITING_ORGANIZATION, WAITING_PLATFORM, RESOLVED, CLOSED.

### Actors
Customer, Provider, Organization, Platform Team, System.

## Business Rules
BR-04-061 through BR-04-068 (see `04_BUSINESS_RULES.md`). The single most important rule here is **BR-04-068**: if an Exception affects a Session, the Session's state machine and the Exception's state machine are managed **independently** (e.g. Session = IN_PROGRESS while Exception = UNDER_REVIEW).

## reference implementation Examples
Customer not home; family doesn't open the door; provider arrived late; provider cannot perform the service; overtime request not agreed; customer won't confirm completion; GPS not recorded; required photo not submitted; need to call the company; need to call the platform team.

## Design Decision — ADR-04-010
Exception is modeled as an **independent entity**: it has its own state machine, own timeline, own interactions, own evidence, and own audit trail, and only *relates to* a Session rather than being *part of* it. This lets the same engine later serve complaints, quality, or any other future process.

## Non-Functional Requirements
- Every Exception must be assignable to a clear owner (Organization or Platform Team) at creation.
- Exception resolution must always be recorded, even as "No Action Required" — an Exception can never be silently abandoned.

## Edge Cases (structural, non-legal)
- Multiple open Exceptions on the same Session must be trackable independently without one blocking or overwriting another.
- An Exception that outlives the Session's own closure must still be resolvable/closeable afterward (an Exception is never deleted, only closed, per BR-04-067).

## Future Extension
- Reuse of this exact engine for post-service complaints, quality reviews, and disputes in future modules — explicitly anticipated in Discovery.

## Open Questions
- The ~30–50 structural exception scenario catalogue mentioned in Discovery as a target ("تقریباً ۳۰ تا ۵۰ سناریو") was not fully enumerated in this conversation; only the categories, severities, and independent-lifecycle architecture were finalized. A full scenario catalogue (excluding the explicitly deferred legal/crisis scenarios) remains a natural follow-up task.

## Related ADR
ADR-04-010 (see `28_ADR.md`)

## Related Domain Objects
Exception, ServiceSession, Interaction, EvidenceItem
