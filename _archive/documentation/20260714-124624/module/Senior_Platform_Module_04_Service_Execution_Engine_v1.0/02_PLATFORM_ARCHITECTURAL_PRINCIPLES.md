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

# 02 — Platform Architectural Principles v1.0

**Status:** Accepted (Living Document)
**Scope:** Entire Architecture Framework
**Applies To:** Module 01+, all future modules, all future implementations

> This document sits above all modules. It is not an ADR of Module 04 — it is the architecture's constitution, first written during Module 04 Discovery once its patterns became clear across four modules.

## 1. Vision

The purpose of this architecture is not to build a single multi-domain platform. The purpose is to establish a reusable architectural framework for building independent service marketplace applications. Each implementation remains an independent software product with its own source code, repository, database, deployment, server, domain name, branding, and business rules. Only the architectural patterns are shared.

## 2. Independent Product Principle

Each implementation is a standalone product (e.g. reference implementation Platform, Beauty Marketplace, Cleaning Marketplace), each with its own repository, database, server, and domain. No runtime dependency exists between implementations. "Generic" does **not** mean multi-tenant or multi-business in one runtime.

## 3. Pattern Before Implementation

Architecture is designed as reusable patterns; implementations adapt those patterns to their own business domain (e.g. Session Lifecycle → Service Session in reference implementation, Appointment Session in Beauty).

## 4. Domain Isolation

Business terminology must never leak into reusable architecture. Patterns use neutral concepts: Customer, Provider, Organization, Request, Assignment, Session, Activity, Interaction, Timeline. Business-specific terminology belongs only inside implementation mappings.

## 5. Event-Driven Architecture

Everything important happens because an Event occurred:

```text
Action → Event → Interaction → Decision → State Change → Timeline → Notification
```

Events are immutable.

## 6. Timeline Is the Operational History

Timeline is the chronological history of operational activities: events, activities, interactions, reviews, corrections, and system decisions. Timeline is not a business object; it is an operational history layer.

## 7. Immutable Operational Records

Operational records never change after creation. Instead of editing, a Review, Correction, Administrative Note, or Audit Record is appended. Deletion is prohibited.

## 8. Configuration Over Hardcoding

Business behavior should be configurable whenever practical (by Organization, Service Type, Session Type, Risk Level, Country, future regulatory requirements). Avoid hard-coded business rules.

## 9. Interaction-Centric Design

The primary interaction model is Interaction, not Message. Messages are only one interaction type; Interaction also includes Approval, Rejection, Confirmation, Signature, Rating, Feedback, Escalation, Request, Response, and Operational Decision.

## 10. Activities Represent Work

Activities represent work performed during a Session. The framework never assumes what that work is; domain implementations define actual activities.

## 11. Observations Represent Facts

The Observation Engine stores observations, not business meaning (e.g. a "Measurement" is a blood-pressure reading in reference implementation, a hair-color formula in Beauty — same architecture, different implementation).

## 12. Evidence Supports Verification

Evidence exists to support operational verification. It does not replace medical records, legal archives, or clinical documentation.

## 13. Separation of Responsibility

Each engine owns one responsibility only (Session Engine → session state, Activity Engine → performed work, Observation Engine → recorded facts, Interaction Engine → actor communications, Evidence Engine → supporting material, Timeline → operational history). No engine owns another engine's responsibility.

## 14. Generic First

Before introducing a domain concept, ask: *can this be expressed as a reusable architectural pattern?* If yes, it belongs in the framework. If no, it belongs in the implementation.

## 15. Business Mapping Layer

Every implementation maps patterns into business language (e.g. Provider → Independent Provider / Company Provider in reference implementation).

## 16. State Machines Before UI

Business state machines must be finalized before UI design. User interfaces implement workflows; they do not define workflows.

## 17. API Follows Domain

APIs expose the domain model. The domain model never changes to simplify APIs.

## 18. Audit by Design

Every important operation must answer: Who? When? Where? Why? Previous State? New State? Trigger? Related Session? Related Event? Audit is a first-class architectural concern.

## 19. Security by Default

Default behavior should be the safest behavior: least privilege, explicit permissions, immutable records, traceable actions, configurable visibility.

## 20. Backward-Compatible Evolution

Framework patterns should evolve through versioning. Changes should avoid breaking existing implementations whenever possible.
