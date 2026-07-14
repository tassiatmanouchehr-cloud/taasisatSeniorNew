# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Purpose
Delivery Tracking records job lifecycle, attempts, provider outcomes and user engagement.

## 2. Delivery Job States
created, queued, sending, sent, delivered, failed, retrying, permanently_failed, skipped, expired, cancelled.

## 3. Engagement States
opened, read, clicked, replied, acknowledged.

## 4. Attempt Tracking
Each provider call creates an attempt with timing, result, provider message ID, response code, normalized error and latency.

## 5. Skip Reasons
rule_disabled, condition_false, missing_template, invalid_recipient, preference_blocked, consent_missing, quiet_hours, channel_disabled, provider_unavailable, duplicate, expired.

## 6. Idempotency
Job idempotency key = event_id + rule_id + recipient_id + channel_type + template_version_id.

## 7. Metrics
created, queued, sent, delivered, failed, retry_count, latency, provider_failure_rate, channel_success_rate.
