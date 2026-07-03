# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## Communication Session
created → processing → completed
created → processing → partially_completed
created → processing → failed
created → expired
processing → cancelled

## Delivery Job
created → queued → sending → sent → delivered
created → queued → sending → failed → retrying → queued
failed → permanently_failed
queued → expired
created → skipped

## Template Version
Draft → Review → Approved → Deprecated → Archived

## Announcement
Draft → Scheduled → Published → Expired → Archived

## Campaign
Draft → Review → Approved → Scheduled → Running → Completed
Draft → Cancelled
Running → Paused → Running
Running → Failed

## Conversation
Open → Pending → Resolved → Archived
Open → Closed
