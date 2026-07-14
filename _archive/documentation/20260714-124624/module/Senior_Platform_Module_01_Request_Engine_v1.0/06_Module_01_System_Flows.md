# Generic Service Marketplace Framework — Module 01: Request Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is the intake foundation of the Generic Service Marketplace Framework. It is frozen and treated as the baseline for all downstream modules (Matching, Provider, Company, Payment, and others). Later modules must not change Module 01 decisions unless a major architectural conflict is discovered.


# System Flows

## Flow 1 — Standard Request Creation

```text
User enters (guest allowed)
↓
Choose service OR describe service recipient
↓
Step-by-step form (fields, text, files)
↓
AI suggests file types → user confirms/corrects
↓
Identity captured at final step (mobile + code + info)
↓
Validation (sufficient?)
↓
Request created, tracking number issued, RequestCreated event
↓
Targeted publishing to eligible providers
↓
Applications collected
↓
Handoff to Module 02
```

## Flow 2 — Multi-Service-Need Request

```text
Request
├── Need 1: night nursing
├── Need 2: physiotherapy
└── Need 3: home lab test

Each need stored separately
↓
Published so matching can run per need
↓
Owner may later remove a single need without cancelling the request
```

## Flow 3 — Targeted Publishing

```text
Request published
↓
Filter providers by service + city/coverage + availability + completeness
↓
If pool is large, notify bounded most-relevant subset (not all)
↓
Providers see "N new requests in <city>"
↓
Provider view/apply behaviour recorded as future ranking signal
```

## Flow 4 — Editing After Creation

```text
Owner edits request
↓
If a provider is already selected/confirmed:
  notify that provider first → provider re-confirms changed request
↓
If providers applied but none selected:
  notify applied providers in queue of the change
```

## Flow 5 — Deletion Before Acceptance

```text
Owner deletes request (no provider accepted yet)
↓
Deletion allowed freely
↓
No separate notification to other applicants
↓
Deletion recorded in customer history
```

## Flow 6 — No-Selection Timeout

```text
Request waiting for customer selection
↓
24h passes with no selection → send reminder
↓
Still no response → phone call
↓
Still no response → auto-delete request, keep in customer history
```

## Flow 7 — Selected-Provider Follow-Up

```text
Provider selected & confirmed
↓
~1h before appointment → remind provider (time + location)
↓
At appointment time → ask customer "did the provider arrive?"
↓
If delayed → capture that provider called about delay
```

## Flow 8 — Recurring Need as Contract

```text
Owner requests: every day 8am for 30 days
↓
Create Contract with 30 sessions
↓
Owner may cancel a single session
↓
If provider unavailable for a session:
  company proposes replacement + platform assists + customer informed
```

## Flow 9 — Platform Protection

```text
Request active / chat active
↓
Scan for off-platform bypass:
  phone number in chat / photo / PDF, external price, cancel-after-arrival
↓
Raise ProtectionSignal
↓
Support reviews → action or dismiss
```

## Flow 10 — Freeze & Handover

```text
Module 01 business + edge cases + enterprise + future criteria met
↓
Generate Journal, Business Decisions, Architecture Notes, Handover
↓
Freeze Module 01
↓
Start Module 02
```
