# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## Invoice Paid Flow
```text
InvoicePaid Event
  ↓
Rule Match: invoice_paid.*
  ↓
Audience: customer, provider, organization, platform_owner
  ↓
Channels: SMS/Email/Push/Inbox/Dashboard/Audit
  ↓
Templates per audience/channel
  ↓
Delivery Jobs
  ↓
Provider/Internal Delivery
  ↓
Tracking + Audit + Timeline
```

## Assignment Created Flow
```text
AssignmentCreated Event
  ↓
Notify customer + provider
  ↓
Create provider read-tracked message
  ↓
If unread after configured delay
  ↓
Escalate to organization admin
  ↓
If unresolved
  ↓
Escalate to platform operator
```

## Campaign Flow
```text
Campaign Approved
  ↓
Segment Audience
  ↓
Apply consent + suppression
  ↓
Throttle jobs
  ↓
Send through channels
  ↓
Collect metrics
```
