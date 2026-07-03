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

# 06 — Domain Model

## Core Entities

### ServiceSession
The central execution entity; owns the Session Lifecycle state machine (see `07_STATE_MACHINES.md`).

### PresenceRecord
A captured location/presence event tied to a Session (en route, arrived, departed).

### StartChecklistInstance
A checklist run tied to one Session's start, made of StartChecklistItems.

### ExecutionActivity
One recorded unit of work performed during a Session. Category-only at Core level (TASK, CHECK, ACTION, OBSERVATION, MEASUREMENT, COMMUNICATION, SYSTEM_EVENT, CUSTOM_EVENT).

### ObservationRecord / NoteRecord / MeasurementRecord / DomainFieldRecord
Structured facts recorded during a Session; Core holds structure only, meaning lives in the implementation mapping.

### EvidenceItem
A piece of supporting material (photo, video, audio, voice note, file, signature, GPS snapshot, checklist attachment, confirmation, approval, review) tied to a context (Session, Activity, Observation, Checklist Item, Completion Request, Exception, Operational Review).

### Interaction
A single actor-to-actor exchange of any kind (message, call, approval, rejection, confirmation, request, response, rating, feedback, signature, escalation, operational decision, internal comment, system prompt).

### Exception
An independent record of anything disrupting normal Session execution; has its own lifecycle, timeline, interactions, evidence, and audit.

### ExtensionRequest
A request to extend a Session's duration, requiring mutual agreement.

### CompletionRecord
The record of Provider completion and Customer confirmation (or Operational Review resolution) for a Session.

### HandoverRecord
The record of what happens to the Service Case once a Session closes (remaining sessions, next planned session, progress).

### Timeline
The chronological operational history layer (not a business object) aggregating events, activities, interactions, reviews, corrections, and system decisions for a Session.

### AuditEntry
Attribution record: who, when, where, why, previous state, new state, trigger, related session, related event.

## Key Relationships

```text
ServiceSession 1..n PresenceRecord
ServiceSession 1..1 StartChecklistInstance
ServiceSession 1..n ExecutionActivity
ServiceSession 1..n ObservationRecord / NoteRecord / MeasurementRecord
ServiceSession 1..n EvidenceItem
ServiceSession 1..n Interaction
ServiceSession 0..n Exception
ServiceSession 0..n ExtensionRequest
ServiceSession 1..1 CompletionRecord
ServiceSession 1..1 HandoverRecord
ServiceSession 1..n Timeline entries
ServiceSession 1..n AuditEntry

ExecutionActivity 0..n EvidenceItem
ExecutionActivity 0..n ObservationRecord
ExecutionActivity 0..1 Event

Exception 0..n EvidenceItem
Exception 0..n Interaction
Exception 1..1 Resolution
```

## reference implementation Mapping (Core → Domain)

| Core | reference implementation |
|---|---|
| Customer | Customer or Customer Delegate |
| Provider | Independent Provider / Organization Provider |
| Organization | Organization |
| ServiceSession | Service Session |
| ExecutionActivity (ACTION) | تعویض پانسمان، کمک در راه رفتن، استحمام، تغذیه، جابه‌جایی Customer |
| ExecutionActivity (MEASUREMENT) | فشار خون، قند خون |
| ObservationRecord | وضعیت Customer، فشار خون، دما، ضربان قلب، اکسیژن خون، تغذیه، آب، تحرک، درد، خلق‌وخو، خواب، زخم، ریسک سقوط، وزن، قد |
| EvidenceItem | عکس، امضا، مدرک مراقبتی |
| Interaction | پیام، تماس، تایید، اعتراض |
| Exception | Customer در منزل نیست، Provider دیر رسیده، اختلاف اضافه‌کاری |

## Related Domain Objects (cross-module)

- Request, RequestServiceNeed (Module 01)
- SelectionLock (Module 02)
- ServiceCase, ServiceAssignment (Module 03) — ServiceSession here is the execution-time counterpart of Module 03's scheduled ServiceSession
