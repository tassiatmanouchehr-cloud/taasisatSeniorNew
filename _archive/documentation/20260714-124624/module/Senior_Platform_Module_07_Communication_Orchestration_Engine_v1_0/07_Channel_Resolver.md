# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Purpose
The Channel Resolver chooses channels per recipient and rule.

## 2. Inputs
- rule channel policy
- tenant channel configuration
- platform channel configuration
- recipient capabilities
- user preferences
- consent state
- intent and priority
- quiet hours
- provider availability

## 3. Supported Channels
sms, email, push, in_app, inbox, dashboard, web_notification, mobile_notification, chat, announcement, webhook, voice, future.

## 4. Decision Outcomes
send, skip_disabled, skip_unavailable, skip_preference, skip_consent, skip_quiet_hours, fallback, audit_only.

## 5. Mandatory Channel Logic
Critical/security/legal/financial messages may require at least one successful channel or audited escalation.

## 6. Fallback Order Example
SMS → Push → Email → In-App → Dashboard escalation.

## 7. Channel Invariants
- A channel cannot be selected without an active provider unless it is internal.
- Marketing channels require consent.
- Quiet hours apply unless bypass is permitted.
- User preferences cannot suppress mandatory critical communication without an approved fallback.
