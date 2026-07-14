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

# 14 — Evidence Engine (Supporting)

## Purpose
Record, retain, and control access to the material evidence that proves a Session's key facts: presence, start, activity, problem, completion, and confirmation.

## Business Goal
Make disputes resolvable with proof, without turning the platform into a medical or legal archive.

## Functional Specification

### Evidence Types
PHOTO, VIDEO, AUDIO, VOICE_NOTE, FILE, SIGNATURE, GPS_SNAPSHOT, CHECKLIST_ATTACHMENT, CUSTOMER_CONFIRMATION, PROVIDER_DECLARATION, ORGANIZATION_APPROVAL, PLATFORM_REVIEW.

### Evidence Lifecycle
```text
CAPTURED → ATTACHED → SUBMITTED → ACCEPTED
```
Exception states: REJECTED, FLAGGED, UNDER_REVIEW, REPLACED_BY_NEW_EVIDENCE, ACCESS_RESTRICTED.

## Business Rules
BR-04-046 through BR-04-052 (see `04_BUSINESS_RULES.md`).

## reference implementation Implementation Note
Evidence in Generic Service Marketplace Framework Reference Implementation supports operational verification only — it is explicitly **not** allowed to become a medical archive or clinical documentation store (BR-04-051).

## Non-Functional Requirements
- Storage must guarantee immutability of the original file and its metadata.
- Retention policy must be enforceable per configured duration (30/90/180 days, 1 year, custom).

## Edge Cases (structural, non-legal)
- Required evidence missing at a mandatory point (e.g. start photo required but not captured) — must produce `evidence_required_missing` rather than silently allowing progression.
- Evidence later disputed — handled via a Review/Flag/Rejection record, never by altering or deleting the original (BR-04-048).

## Future Extension
- Legal hold on evidence retention — explicitly deferred, not part of Module 04.

## Open Questions
- None beyond the explicitly deferred legal hold topic.

## Related ADR
Inherits ADR-04-001 (Immutable Records).

## Related Domain Objects
EvidenceItem, ExecutionActivity, ObservationRecord, Exception, ServiceSession
