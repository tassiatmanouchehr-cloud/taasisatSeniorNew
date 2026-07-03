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

# 13 — Observation & Notes Engine (Supporting)

## Purpose
Record any observation, note, report, status, measurement, or operational remark made during a Session, without the Core engine assigning it business meaning.

## Business Goal
Give providers, customers, organizations, and the platform team a shared, structured, permission-aware place to record facts — reusable across completely different domains (a blood-pressure reading and a hair-color formula are the same Core structure).

## Functional Specification

### Core Objects
Observation Record, Note Record, Measurement Record, Domain Field Record, Correction Record, Review Record, Audit Record.

### Record Categories
GENERAL_NOTE, OPERATIONAL_NOTE, CUSTOMER_NOTE, PROVIDER_NOTE, INTERNAL_NOTE, OBSERVATION, MEASUREMENT, WARNING, FOLLOW_UP_REQUIRED, DOMAIN_SPECIFIC_RECORD.

## Business Rules
BR-04-037 through BR-04-044 (see `04_BUSINESS_RULES.md`).

## reference implementation Implementation

In Generic Service Marketplace Framework Reference Implementation, this engine can record: service observations, measurements, evidence, condition notes, provider observations and customer notes as configured by the reference implementation.

## Non-Functional Requirements
- Core schema must remain meaning-agnostic; `field_key` + `value` + `unit` pattern rather than named medical columns.
- Visibility enforcement must be checked on every read, not only on write.

## Edge Cases (structural, non-legal)
- A critical observation (e.g. a warning-level measurement) must be able to trigger an event (BR-04-043) without the Observation Engine itself owning escalation logic — that belongs to the Exception & Resolution Engine.
- Internal notes must never leak to Customer visibility even via aggregate views (BR-04-044).

## Future Extension
- Structured, versioned "normal range" reference tables per measurement type and region.
- Domain-specific observation form builders per Organization.

## Open Questions
- None explicitly raised beyond the measurement-unit versioning already captured in BR-04-042.

## Related ADR
Inherits ADR-04-001 (Immutable Records).

## Related Domain Objects
ObservationRecord, ExecutionActivity, ServiceSession, EvidenceItem
