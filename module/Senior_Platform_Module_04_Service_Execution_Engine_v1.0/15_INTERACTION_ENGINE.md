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

# 15 — Interaction Engine (Primary)

## Purpose
Manage every operational exchange between actors during a Session — not as a general-purpose chat system, but as a structured mechanism for resolving operational needs.

## Business Goal
Reduce support call volume, keep a complete record of every operational exchange, manage disputes, log operational decisions, and create a full audit trail — while explicitly staying out of the business of being a social network or general messenger.

## Functional Specification

### What This Engine Is For
Customer has a question; provider is running late; customer requests overtime; provider requests help; the company needs to call; the platform team needs to step in; a dispute has arisen.

### What This Engine Is Not For
Everyday chit-chat, casual conversation, stickers, unrelated file sharing.

### Communication / Interaction Types
INFORMATION, QUESTION, REQUEST, APPROVAL_REQUEST, STATUS_UPDATE, ISSUE_REPORT, HELP_REQUEST, CUSTOMER_MESSAGE, PROVIDER_MESSAGE, ORGANIZATION_MESSAGE, SYSTEM_MESSAGE, OPERATIONAL_CALL_REQUEST — generalized under the broader Interaction taxonomy: Message, Phone Call, Approval, Rejection, Confirmation, Request, Response, Rating, Feedback, Signature, Escalation, Operational Decision, Internal Comment, System Prompt.

### Conversation Pairings
Customer↔Provider, Customer↔Organization, Provider↔Organization, Organization↔Platform Team, Customer↔Platform Team (special cases only), System→Everyone.

### Communication / Interaction Status
OPEN, WAITING_RESPONSE, IN_PROGRESS, RESOLVED, CLOSED, ESCALATED.

### Core Interaction Object
Interaction ID, Interaction Type, Sender, Recipients, Related Session, Related Activity, Related Event, Priority, Status, Visibility, Payload, Attachments, Requires Response, Due Time, Resolution, Timeline Position, Audit Metadata.

## Business Rules
BR-04-053 through BR-04-060 (see `04_BUSINESS_RULES.md`).

## Platform-Wide Design Decisions
- **ADR-04-008 — Platform-Controlled Communication:** all operational communication happens inside the platform; the platform mediates. Real phone numbers are never revealed between customer and provider while a session is active.
- **ADR-04-009 — Universal Interaction Architecture:** the base concept is Interaction, not Message — because during an active session, actors are constantly interacting (declaring start, confirming completion, approving overtime, rejecting a dispute, rating a service), and modeling all of that as one Interaction type lets every future module (invoice approval, payment confirmation, complaint, quality review, dispute resolution, refund approval) reuse the same engine.

## Non-Functional Requirements
- Every interaction must be traceable to a Session, Sender, and Recipient — no orphaned exchanges.
- The engine must never expose real contact details between customer and provider.

## Edge Cases (structural, non-legal)
- A resolved issue's thread must transition to Closed rather than remaining silently Open (BR-04-060).
- A phone call must itself be recorded as an event (duration, result, follow-up-required), not merely referenced informally (BR-04-059).

## Future Extension
- WhatsApp / IVR / auto-call channel integration.
- Interaction-based workflows for future modules (Module 05+ invoice approval, disputes, quality review, refunds) reusing this exact engine.

## Open Questions
- None explicitly raised beyond channel-specific future extensions above.

## Related ADR
ADR-04-007, ADR-04-008, ADR-04-009 (see `28_ADR.md`)

## Related Domain Objects
Interaction, ServiceSession, Exception, ExtensionRequest, CompletionRecord
