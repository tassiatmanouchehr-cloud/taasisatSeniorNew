# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Purpose
Audit and Timeline provide evidence for support, disputes, compliance and operations.

## 2. Audit Questions
Why was a message sent? Why skipped? Who received it? Which channel? Which template version? Which provider? Was it delivered? Was it read? Did it fail? Was it retried?

## 3. Timeline
Every major entity may expose communication timeline:
request, match, booking, service execution, invoice, payment, trust case, dispute, user, tenant, custom entity.

## 4. Timeline Entry
created, queued, sent, delivered, failed, retried, read, clicked, acknowledged, escalated, skipped.

## 5. Rules
- Audit records are immutable.
- Sensitive content should be hashed or redacted.
- Access to communication evidence is permission-controlled.
