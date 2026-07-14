# Generic Service Marketplace Framework

**Module 03 — Booking, Assignment & Service Activation Engine**

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Frozen |
| **Document Owner** | Product Architecture |
| **Project** | Generic Service Marketplace Framework Reference Implementation |
| **Module Owner** | Platform Owner |
| **Depends On** | Module 01 — Request Engine, Module 02 — Matching Engine |
| **Next Modules** | Module 04 — Service Execution / Care Delivery Engine, Module 05/06 — Payment & Settlement |
| **Language** | Persian business domain, English technical structure |

> Module 01 and Module 02 are Frozen and Approved and are treated as baseline. Module 03 must not change their decisions unless a major architectural conflict is discovered.

# 02 — Product Specification

## Purpose

Turn a customer/family's locked selection into a confirmed, provider-committed, coordinated Service Assignment, ready for real-world service delivery.

## Business Goal

Guarantee that "selected" reliably means "someone is actually coming," across all three provider models (independent provider, company provider, company package), while protecting both customer and provider from silent failure.

## Terminology (Ubiquitous Language)

| Term | Meaning |
|---|---|
| Selection Lock | Temporary hold on a candidate/option the customer chose, produced by Module 02 |
| Final Confirmation | Customer's and provider's explicit agreement to proceed under the stated terms |
| Provider Commitment | The binding acceptance by the actual responsible party (provider or company) |
| Service Case | The operational case record that Module 03 builds and Module 04 will execute against |
| Service Assignment | The formal link between a Service Case (or one of its needs) and a committed provider |
| Assignment Plan | A set of Assignments covering all service needs of a multi-need request |
| Service Session | One scheduled occurrence of care within a Service Case (single visit or one session of a contract) |
| Pre-Service Coordination | The operational choreography before care starts: confirmation, reminders, en-route, arrival |
| Booking State Machine | The status model covering Selection Lock → Confirmed Assignment |
| Customer or Customer Delegate | Customer-side actor |
| Independent Provider | Independent provider |
| Organization Provider | Company-affiliated provider |
| Organization | Provider company |
| Platform Owner | Platform owner |

## Actors

- Customer / Family
- Independent Provider
- Company Provider
- Company (company admin/dispatcher)
- Support Operator
- Platform Owner
- System / Booking Engine

## Functional Specification

### FR-301 — Selection Lock Consumption
Module 03 receives a Selection Lock from Module 02 and manages its validity window, renewal, and expiry.

### FR-302 — Provider Commitment (Three Paths)
The module supports three separate commitment paths:

- **Independent provider:** the provider personally commits.
- **Company provider:** commitment is owned by the company; the company may substitute the provider under rules (see BR-3xx).
- **Company package:** the customer selected the company, not a specific person; the company assigns provider(s) under rules.

### FR-303 — Assignment Creation
On commitment, the system creates a Service Assignment (or an Assignment Plan for multi-need requests), linked to the relevant Service Need(s).

### FR-304 — Service Case Creation
A Service Case is created to hold the operational record: customer, provider/company, address, timing, agreed terms, and linked Assignments/Sessions.

### FR-305 — Session Scheduling
The first Service Session (and, for contracts, the full session schedule) is created from the confirmed timing.

### FR-306 — Pre-Service Coordination
The system coordinates confirmation, reminders, en-route signalling, and arrival checks before the first session starts.

### FR-307 — No Redundant Summary Screen
Customer and provider each see live Service Case status inside their own panel; a separate one-off "confirm this summary" screen is not required (decided in Discovery, scenario 1).

### FR-308 — Manual Hold
Platform Owner / authorized support can place a Service Case on hold before service start if a risk is identified (documents, suspension, complaints, repeated cancellations).

### FR-309 — Non-Response Escalation
If a provider has not signalled "on the way" close to appointment time, the system immediately contacts the provider and involves the company (if applicable), rather than only sending a passive reminder.

### FR-310 — Service Activation Boundary
The module's responsibility ends the moment "Service Started" is recorded by the provider; from that point the Service Case is owned by Module 04.

### FR-311 — Role Dashboards
Each role (customer, provider, company, Platform Owner) has a dashboard reflecting live Module 03 state relevant to them.

### FR-312 — Audit & Traceability
Every commitment, assignment, hold, and provider change is attributable and logged.

## Non-Functional Requirements

- Event-driven: state changes emit events consumed by dashboards, notifications, and Module 04.
- Auditability of every manual and automatic transition.
- Configurability by Platform Owner (lock TTL, escalation timing, hold policy).
- Resilience: provider or customer inaction must never leave a Service Case silently stuck.
- Fairness: consistent with Module 01's "Platform First" principle — no side is unconditionally favored.

## MVP Philosophy

Version 1 must guarantee that a confirmed booking is real and trackable across all three provider models, with clear escalation when confirmation stalls — while deferring the legally sensitive crisis-scenario catalogue to a dedicated future session with legal input.
