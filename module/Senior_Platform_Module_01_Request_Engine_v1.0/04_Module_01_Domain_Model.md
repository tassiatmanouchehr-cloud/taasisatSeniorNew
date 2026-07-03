# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# Domain Model

## Core Entities

### Request
The central entity: a service request created by a family/customer. Owns status, timeline, and one or more service needs.

### RequestServiceNeed
A specific service inside a request.

Examples:

- Night nursing
- Physiotherapy
- Home lab test
- Bathing / daily care
- Injection

### CareReceiver
The service recipient person or customer the request is for. May differ from the request owner (e.g. a child creating a request for a parent).

### RequestOwner
The family member or customer who creates and controls the request.

### RequestAttachment
A file attached to the request.

Fields:

- file reference (compressed)
- suggested_type (from AI)
- confirmed_type (from user)
- size
- visibility scope

### ValidationResult
Stores whether a request is sufficient to publish and, if not, the reasons.

### Publication
A record of a request being published to a bounded set of eligible providers.

### Application
A provider's declaration of willingness (اعلام آمادگی) for a published request.

### Contract
A recurring commitment created from a recurring request.

### Session
One occurrence inside a Contract.

### RequestTimelineEntry
A single chronological event visible to permitted roles.

### RequestEvent
An emitted domain event consumed by other modules.

### ProtectionSignal
A flag raised when an off-platform bypass attempt or abuse pattern is detected.

### CustomerRequestHistory
Per-customer log of created, edited, and deleted requests (retained even after deletion).

## Key Relationships

```text
RequestOwner 1..n Request
Request 1..1 CareReceiver
Request 1..n RequestServiceNeed
Request 0..n RequestAttachment
Request 1..1 ValidationResult
Request 0..1 Publication
Request 0..n Application
Request 0..1 Contract
Contract 1..n Session
Request 1..n RequestTimelineEntry
Request 1..n RequestEvent
Request 0..n ProtectionSignal
RequestOwner 1..1 CustomerRequestHistory
```

## Request Life Cycle (summary)

```text
DRAFT
WAITING_FOR_VALIDATION
PUBLISHED
RECEIVING_APPLICATIONS
WAITING_FOR_CUSTOMER_SELECTION
PROVIDER_SELECTED
CONFIRMED
SERVICE_STARTED
COMPLETED
CANCELLED
```

`CANCELLED` (and deletion) can be reached from several earlier states under the cancellation rules; full transitions are in the State Machines document.
