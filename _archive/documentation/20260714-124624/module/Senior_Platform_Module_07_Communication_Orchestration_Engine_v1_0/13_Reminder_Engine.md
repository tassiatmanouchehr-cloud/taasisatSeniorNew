# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Purpose
The Reminder Engine creates scheduled and repeated communication based on time or state.

## 2. Reminder Types
one_time, recurring, interval_based, deadline_based, state_based, escalation_based.

## 3. Examples
upcoming service reminder, unpaid invoice reminder, missing confirmation reminder, expiring document reminder, provider response reminder.

## 4. Flow
Reminder definition → schedule evaluation → state check → CES/system communication event → normal communication pipeline.

## 5. Rules
- Reminders must not bypass preferences unless mandatory.
- Reminders must expire when target state no longer applies.
- Reminder executions must be audited.
