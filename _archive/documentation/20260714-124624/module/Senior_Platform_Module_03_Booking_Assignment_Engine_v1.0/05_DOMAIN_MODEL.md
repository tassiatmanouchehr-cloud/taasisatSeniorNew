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

# 05 — Domain Model

## Core Entities

### SelectionLock
Carried over from Module 02; managed (TTL, renewal, expiry) inside Module 03.

### ServiceCase
The operational case record: customer, provider/company, address, agreed terms, linked Assignments and Sessions. Created once commitment begins to succeed.

### ServiceAssignment
Formal link between a Service Need (or package) and a committed provider (provider or company).

### AssignmentPlan
A set of Assignments covering all service needs of a multi-need request.

### ServiceSession
One scheduled occurrence of care within a Service Case.

### ProviderCommitment
Records the commitment decision (accept/reject/timeout) and which path (independent / company provider / company package) produced it.

### CoordinationEvent
A pre-service coordination milestone: reminder sent, en-route signalled, arrival confirmed, non-response escalation triggered.

### ManualHold
A Platform Owner/support-initiated hold on a Service Case before service start.

### AuditEntry
Attribution record for who selected, confirmed, assigned, substituted, or intervened.

## Key Relationships

```text
SelectionLock 1..1 ServiceNeed (from Module 01/02)
ServiceCase 1..n ServiceAssignment
AssignmentPlan 1..n ServiceAssignment
ServiceAssignment 1..1 ProviderCommitment
ServiceCase 1..n ServiceSession
ServiceCase 0..n CoordinationEvent
ServiceCase 0..n ManualHold
ServiceCase 1..n AuditEntry
```

## Provider Commitment Paths (Domain View)

```text
IndependentProvider  → commits personally           → ServiceAssignment
CompanyProvider      → company owns commitment       → ServiceAssignment (provider substitutable)
Company (package)  → company assigns provider(s) later → ServiceAssignment(s)
```

## Related Domain Objects (cross-module)

- Request, RequestServiceNeed (Module 01)
- MatchCandidate, CustomerSelection (Module 02)
- Care Delivery Record (Module 04, not owned here)
