# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Purpose
The Inbox Engine provides persistent in-platform communication for web and mobile.

## 2. Features
unread/read, archive, hide/delete, pin, priority, category, action URL, entity reference, grouping, expiry, badge count.

## 3. Inbox Item Fields
recipient, title, body, category, priority, entity_reference, action_url, read_at, archived_at, expires_at.

## 4. Use Cases
payment confirmation, assignment updates, dispute notices, reminders, announcements, support messages.

## 5. Rules
- Inbox messages must be tenant-isolated.
- Read receipts must be tracked.
- Critical inbox items may require acknowledgement.
- Expired items may remain in audit but disappear from active inbox.
