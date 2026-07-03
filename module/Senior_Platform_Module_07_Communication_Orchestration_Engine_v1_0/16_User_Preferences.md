# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Purpose
User Preferences define how users receive communication.

## 2. Hierarchy
Framework default → Platform policy → Tenant override → Role policy → User preference → Critical override.

## 3. Preference Dimensions
event_type, intent, channel, frequency, quiet_hours, locale, timezone, consent state.

## 4. Opt-Out Rules
Marketing can be disabled. Informational may be limited. Transactional, financial, security, legal, dispute and critical messages cannot be fully suppressed unless platform policy defines a safe alternative.

## 5. Consent
Consent must be tracked separately for marketing and transactional communication where applicable.

## 6. Suppression Lists
Suppression lists block selected channels or addresses due to bounce, unsubscribe, complaint, legal or admin action.
