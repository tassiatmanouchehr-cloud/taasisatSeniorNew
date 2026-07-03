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

# 07 — Flows

## Flow 1 — Independent Provider Path

```text
Customer selects independent provider candidate
↓
Selection Lock created
↓
Provider notified, must accept within commitment window
↓
If accepted: ServiceAssignment CONFIRMED
↓
Service Case created, first Session scheduled
↓
Pre-Service Coordination begins
```

## Flow 2 — Company Provider Path

```text
Customer selects company-provider candidate
↓
Selection Lock created
↓
Company notified; company owns commitment
↓
Company confirms (with the named provider, or substitutes under BR-309)
↓
If substituted and customer had a specific-person expectation: customer informed
↓
ServiceAssignment CONFIRMED
↓
Service Case created, Session scheduled
```

## Flow 3 — Company Package Path

```text
Customer selects company as package (not a specific provider)
↓
Selection Lock created
↓
Company commits at the company level
↓
Company assigns provider(s) to cover the needed services
↓
Customer is informed who is coming (no per-provider approval required in MVP)
↓
ServiceAssignment(s) CONFIRMED → AssignmentPlan
↓
Service Case created, Sessions scheduled
```

## Flow 4 — Multi-Need Assignment Plan

```text
Request has Need 1, Need 2, Need 3
↓
Each Need goes through its own commitment path (independently)
↓
Assignments aggregate into an AssignmentPlan
↓
Service Case reflects mixed per-need status until all are confirmed
```

## Flow 5 — Pre-Service Coordination

```text
Assignment confirmed, Session scheduled
↓
Pre-appointment reminder sent to provider
↓
Provider signals "on the way"
↓
If not signalled close to appointment time:
  system immediately contacts provider AND involves company (BR-318)
↓
At appointment time: customer asked "did the provider arrive?"
↓
Arrived → Service Started → handoff to Module 04
```

## Flow 6 — Commitment Failure & Recovery

```text
Provider does not accept within window
↓
ServiceAssignment FAILED
↓
Service Need returns toward Matching / operator attention
↓
Customer notified
```

## Flow 7 — Selection Lock Expiry

```text
Selection Lock TTL elapses before commitment
↓
Lock EXPIRED → RELEASED
↓
Customer notified; option returns toward Matching
```

## Flow 8 — Manual Hold

```text
Platform Owner/support identifies a risk (documents, suspension, complaints, repeat cancellations)
↓
Service Case placed ON_HOLD, with reason logged
↓
Case is not eligible to reach READY_TO_START while on hold
↓
Support releases hold or cancels the case
```

## Flow 9 — Dashboards (Live View, No Redundant Summary Screen)

```text
Customer panel shows: next service, provider en route status, last message, next session
Provider panel shows: today's service, start time, route, messages
Company panel shows: today's dispatches, forces en route, problem cases
Platform Owner panel shows: crises, delays, no-shows, replacements
```

## Flow 10 — Handoff to Module 04

```text
Provider taps "Start Service"
↓
Service Started event recorded
↓
Service Case ownership transfers to Module 04
```
