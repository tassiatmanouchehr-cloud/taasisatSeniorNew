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

# 11 — Start Checklist Engine (Supporting)

> **Note on rule numbering:** unlike the other nine engines, this engine's business rules were discussed structurally in Discovery but were not individually numbered (no BR-04-021 through BR-04-028 exist in the source conversation). The rules below are written as descriptive rules, not numbered BR items, to avoid inventing numbering that was never actually assigned.

## Purpose
Validate that a Session is genuinely ready to move into IN_PROGRESS — not merely that the provider has arrived.

## Business Goal
Prevent "arrived" from silently becoming "started" without the minimum proof and agreement the business actually requires.

## Functional Specification

Core purpose: a Session should not start just because the provider reached the location. Real start requires:

```text
Provider Arrived
+ Presence Verified
+ Start Checklist Completed
+ Required Evidence Submitted
+ Customer Confirmation Captured or Exception Recorded
```

### Checklist Types
Generic Start Checklist, Service-Type Checklist, Organization Checklist, Request-Specific Checklist, Risk-Based Checklist, Domain-Specific Checklist.

### Checklist Item Types
BOOLEAN_CONFIRMATION, TEXT_INPUT, NUMBER_INPUT, PHOTO_REQUIRED, SIGNATURE_REQUIRED, CUSTOMER_CONFIRMATION, GPS_CONFIRMATION, FILE_UPLOAD, MULTI_SELECT, SINGLE_SELECT, DOMAIN_FORM_FIELD.

### Descriptive Rules (not individually numbered in Discovery)

- A Session cannot enter IN_PROGRESS without passing its Start Checklist (this rule is formally numbered as BR-04-004 in `04_BUSINESS_RULES.md`, and belongs conceptually to this engine).
- Checklists can be layered: a generic checklist plus a service-type, organization, request-specific, or risk-based checklist can all apply to the same session start.
- If the customer does not cooperate at start, the problem is recorded rather than silently skipped (feeds into the Exception & Resolution Engine).

## Non-Functional Requirements
- Checklist definitions must be data-driven/configurable per Organization and Service Type, not hard-coded.

## Edge Cases (structural, non-legal)
- Customer does not cooperate with required checklist items (e.g. won't provide a signature) — this must produce a recorded start problem rather than blocking indefinitely with no trace.

## Future Extension
- Organization-authored custom checklist templates with their own validation rules (named in scope but not fully specified in Discovery).

## Open Questions
- The exact validation-rule engine for checklist templates (conditional logic, required-if-other-field rules) was flagged as "coming next" in Discovery but not designed before the conversation moved to the Activity Engine; this is a genuine open item, not a deferred legal issue.

## Related ADR
None assigned directly; inherits BR-04-004 from the Session Lifecycle Engine.

## Related Domain Objects
StartChecklistInstance, ServiceSession, EvidenceItem
