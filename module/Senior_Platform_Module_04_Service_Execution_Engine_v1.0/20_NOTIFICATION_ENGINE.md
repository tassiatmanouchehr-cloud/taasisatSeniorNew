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

# 20 — Notification Engine

## Purpose
Deliver Module 04 events to the right recipients through the right channels, continuing the platform-wide Notification Architecture established at the top of this module's Discovery.

## Business Goal
Make sure execution-critical moments (start problems, exceptions, extension requests, completion, disputes) reach the party who needs to act, in a fully configurable way.

## Functional Specification

### Recipients
Customer, Provider, Organization, Platform Team.

### Channels
In-App, Push, SMS, Email, Panel Notification, Phone Call.

### Configurability
Every Event may create different Notifications; each Notification supports different recipients, different templates, and different delivery channels. Nothing is hard-coded — everything is configurable, consistent with Platform Principle 8 (Configuration Over Hardcoding).

### Example Mapping

| Event | Primary Recipient | Default Channel | Escalation |
|---|---|---|---|
| session_ready_for_execution | Provider | Push | — |
| arrival_location_mismatch | Organization, Platform Team | In-App, Push | Manual review flag |
| customer_confirmation_failed | Organization | Panel Notification | Phone Call |
| operational_confirmation_requested | Organization, Platform Team | Push, Panel Notification | Phone Call |
| extension_requested | Customer or Provider (counterpart) | Push | — |
| extension_operational_review_required | Organization, Platform Team | Panel Notification | Phone Call |
| exception_created (HIGH/CRITICAL) | Organization, Platform Team | Push, Panel Notification | Phone Call |
| session_closed | Customer, Provider | In-App | — |
| service_case_updated | Customer, Provider, Organization | In-App | — |

## Business Rules
Inherits the general Notification Architecture stated at Module 04 kickoff: every event may generate notifications; recipients, templates, and channels must all be configurable; nothing is hard-coded.

## Non-Functional Requirements
- Escalation-tier notifications (e.g. confirmation failures, critical exceptions) must be able to bypass normal batching and fire immediately.
- Notification failures must be logged and retried via a fallback channel.

## Edge Cases (structural, non-legal)
- Recipient has all channels disabled — critical events (e.g. unresolved exception, disputed completion) must still surface on the Organization/Platform Team panel, not be silently dropped.

## Future Extension
- WhatsApp / IVR / auto-call channels (consistent with the Interaction Engine's future extension notes).

## Open Questions
- Exact default channel-priority ordering per event type was not fully enumerated in Discovery; the table above is a reasonable default derived from the stated architecture, not a verbatim decision.

## Related ADR
Inherits ADR-04-008 (Platform-Controlled Communication).

## Related Domain Objects
Interaction, Exception, ExtensionRequest, ServiceSession
