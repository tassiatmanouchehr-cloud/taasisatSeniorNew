# Generic Service Marketplace Framework — Module 02: Matching Engine

**Version:** v1.0  
**Status:** Frozen / Approved  
**Project:** Generic Service Marketplace Framework  
**Module Owner:** Platform Architecture Team  
**Language:** Persian business domain, English technical structure  

> Module 01 — Request Engine is frozen and is treated as baseline. Module 02 must not change Module 01 decisions unless a major architectural conflict is discovered.


# System Flows

## Flow 1 — Standard Matching

```text
Approved Request from Module 01
↓
Read RequestServiceNeeds
↓
Run Eligibility per provider and service need
↓
Generate candidates
↓
Broadcast request to eligible candidates
↓
Collect Accept / Reject
↓
Show accepted candidates to customer/family
↓
Rank and update list dynamically
↓
Customer selects candidate
↓
Record selection boundary
↓
Handoff to Module 03
```

## Flow 2 — Multi-Need Request

```text
Request
├── Need 1: care/bathing
├── Need 2: injection
└── Need 3: physiotherapy

For each need:
  eligibility → candidates → accepted candidates

Also generate package candidates:
  independent provider covering multiple needs
  company covering multiple needs
```

## Flow 3 — Company Provider Matching

```text
Check company lifecycle and eligibility
↓
If company not eligible: reject all company providers
↓
If company eligible: check company provider service eligibility
↓
Check availability
↓
Generate company provider candidate
```

## Flow 4 — Candidate Acceptance

```text
Provider receives notification
↓
Accept or Reject
↓
If Accept:
  candidate becomes visible to customer/family
↓
If Reject:
  candidate hidden from customer/family
```

## Flow 5 — Candidate Withdrawal

```text
Accepted candidate withdraws
↓
If not selected:
  remove/update from list
  notify customer if relevant
↓
If selected:
  error/replacement scenario begins in Module 03 or support flow
```

## Flow 6 — Expiry

```text
Matching starts
↓
No customer selection by configurable reminder time, default 24h
↓
Notify customer/family
↓
No selection by configurable expiry time, default 48h
↓
Expire matching
↓
Block late candidate responses
```

## Flow 7 — Reopen Matching

```text
Expired matching
↓
Platform Owner clicks Reopen Matching
↓
System logs action
↓
Matching returns to distribution state
```

## Flow 8 — Manual Intervention

```text
Matching failed or customer dissatisfied
↓
Support reviews matching
↓
Support can rerun ranking or restart matching
↓
Authorized user can suggest candidate transparently
↓
Audit log saved
```
