# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Purpose

The Communication Rule Model defines how CES Events become communication outputs.

A rule answers:
- when to communicate,
- who receives it,
- through which channels,
- which template is used,
- whether it is enabled,
- whether user preferences apply,
- how failures are retried,
- when escalation happens,
- how the decision is audited.

## 2. Rule Structure

```yaml
rule_code: invoice_paid.customer.transactional
enabled: true
event_type: InvoicePaid
intent: financial
priority: high
tenant_scope: inheritable
audience:
  - type: customer
channels:
  sms:
    enabled: true
    template: invoice_paid.customer.sms
  email:
    enabled: true
    template: invoice_paid.customer.email
  push:
    enabled: true
    template: invoice_paid.customer.push
  inbox:
    enabled: true
    template: invoice_paid.customer.inbox
conditions:
  - invoice.status == "paid"
preference_mode: respect_user_except_critical
quiet_hours: bypass_if_financial_high
retry_policy: transactional_standard
fallback_policy: sms_to_email_if_sms_fails
expiration: none
audit: full
```

## 3. Rule Fields

| Field | Required | Description |
|---|---:|---|
| rule_code | yes | Stable identifier |
| enabled | yes | Activation flag |
| event_type | yes | CES event type |
| intent | yes | Communication intent |
| priority | yes | Delivery priority |
| tenant_scope | yes | Global, tenant, organization or role scope |
| audience | yes | Logical recipients |
| channels | yes | Channel definitions |
| template | yes | Template reference per channel |
| conditions | no | Boolean expression over allowed event payload |
| preference_mode | yes | How user preferences apply |
| quiet_hours | no | Quiet hours behavior |
| retry_policy | no | Retry behavior |
| fallback_policy | no | Fallback behavior |
| escalation_policy | no | Escalation behavior |
| expiration | no | Time-to-live |
| audit | yes | Audit depth |

## 4. Activation Hierarchy

Order of evaluation:

1. Framework default
2. Platform owner override
3. Tenant override
4. Organization override
5. Role override
6. Event rule override
7. Audience override
8. Channel override
9. Template availability
10. User preference
11. Emergency or critical override

## 5. Rule Decision Outcomes

- send
- skip_disabled
- skip_condition_false
- skip_user_preference
- skip_missing_consent
- skip_quiet_hours
- skip_missing_template
- skip_invalid_recipient
- skip_channel_unavailable
- send_fallback
- audit_only
- escalate
- dead_letter

Every decision is audited.

## 6. Audience Policy

Audience policy can reference:
- actor
- aggregate owner
- assigned provider
- related organization
- platform team role
- finance team
- trust team
- support team
- custom resolver

Audience policy must be generic and must not hard-code domain roles.

## 7. Channel Policy

Channel policy supports:
- enabled/disabled per channel
- mandatory channels
- optional channels
- fallback order
- quiet-hour behavior
- delivery receipt requirement
- cost controls
- provider preference

## 8. Preference Modes

- ignore_user_preferences
- respect_user_preferences
- respect_user_except_critical
- mandatory_transactional
- mandatory_legal
- marketing_opt_in_required
- audit_only

## 9. Condition Expressions

Conditions may only use:
- CES event fields
- approved event payload fields
- approved read-only resolver outputs
- tenant configuration
- role attributes

Conditions must not perform arbitrary database queries.

## 10. Example: Invoice Paid

Rules:

| Audience | SMS | Email | Push | Inbox | Dashboard | Audit |
|---|---|---|---|---|---|---|
| customer | enabled | enabled | enabled | enabled | disabled | full |
| provider | optional | disabled | enabled | enabled | disabled | full |
| organization | disabled | enabled | disabled | disabled | enabled | full |
| platform_owner | disabled | optional | optional | disabled | enabled | full |

## 11. Example: Provider Assignment Created

Customer:
- SMS enabled
- Push enabled
- Inbox enabled

Provider:
- SMS enabled
- Push enabled
- Inbox enabled

Organization:
- Dashboard enabled

Platform owner:
- Audit enabled

Escalation:
- If provider does not read within configured time, notify organization admin.
- If still unresolved, notify platform operator.

## 12. Rule Versioning

A rule version is immutable after activation. New changes create a new version.

Fields:
- rule_id
- version
- status
- created_by
- approved_by
- effective_from
- effective_until

## 13. Rule Validation

A rule is invalid if:
- event_type is unknown,
- audience resolver is missing,
- enabled channel has no template,
- template variables do not match payload schema,
- mandatory channel has no provider,
- tenant override violates platform policy,
- marketing rule lacks opt-in policy,
- critical rule can be fully disabled without audit.
