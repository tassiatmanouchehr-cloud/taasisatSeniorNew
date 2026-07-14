# Generic Service Marketplace Framework
# Module 07 — Communication Orchestration Engine v1.0

Status: Frozen Candidate
Scope: Generic Service Marketplace
Reference Implementation: Generic Service Marketplace/Home-Care Marketplace only as mapping layer, not core domain
Depends On: CES v1.0 Frozen, CCS v1.0 Frozen, Modules 01–06 Frozen

---

## 1. Purpose

This catalog defines CCS configuration keys used by Module 07.

## 2. Configuration Naming Prefix

All Module 07 configuration keys use:

```text
communication.*
```

## 3. Core Configuration Keys

| Key | Type | Scope | Description |
|---|---|---|---|
| communication.enabled | boolean | global/tenant | Enables the engine |
| communication.event_ingestion.enabled | boolean | global | Enables CES event consumption |
| communication.audit.enabled | boolean | global/tenant | Enables communication audit |
| communication.default_locale | string | global/tenant | Default locale |
| communication.default_timezone | string | global/tenant | Default timezone |

## 4. Rule Configuration

| Key | Type | Scope |
|---|---|---|
| communication.rules.enabled | boolean | global/tenant |
| communication.rules.override_mode | enum | global/tenant |
| communication.rules.require_approval | boolean | global/tenant |
| communication.rules.allow_tenant_override | boolean | global |
| communication.rules.max_active_rules_per_event | integer | global/tenant |

Override modes:
- inherit
- override
- merge
- deny_override

## 5. Channel Configuration

| Key | Type | Scope |
|---|---|---|
| communication.channels.sms.enabled | boolean | global/tenant |
| communication.channels.email.enabled | boolean | global/tenant |
| communication.channels.push.enabled | boolean | global/tenant |
| communication.channels.in_app.enabled | boolean | global/tenant |
| communication.channels.inbox.enabled | boolean | global/tenant |
| communication.channels.dashboard.enabled | boolean | global/tenant |
| communication.channels.chat.enabled | boolean | global/tenant |
| communication.channels.webhook.enabled | boolean | global/tenant |
| communication.channels.voice.enabled | boolean | global/tenant |

## 6. Provider Configuration

| Key | Type | Scope |
|---|---|---|
| communication.providers.sms.default | string | global/tenant |
| communication.providers.email.default | string | global/tenant |
| communication.providers.push.default | string | global/tenant |
| communication.providers.voice.default | string | global/tenant |
| communication.providers.failover.enabled | boolean | global/tenant |
| communication.providers.health_check.enabled | boolean | global |
| communication.providers.credentials.encryption_required | boolean | global |

## 7. Template Configuration

| Key | Type | Scope |
|---|---|---|
| communication.templates.versioning.enabled | boolean | global |
| communication.templates.approval_required | boolean | global/tenant |
| communication.templates.preview.enabled | boolean | global/tenant |
| communication.templates.missing_variable_policy | enum | global/tenant |
| communication.templates.allow_tenant_templates | boolean | global |

Missing variable policy:
- fail
- skip
- render_placeholder
- fallback_template

## 8. Preference and Consent Configuration

| Key | Type | Scope |
|---|---|---|
| communication.preferences.enabled | boolean | global/tenant |
| communication.preferences.user_level_enabled | boolean | global/tenant |
| communication.preferences.role_level_enabled | boolean | global/tenant |
| communication.consent.marketing_required | boolean | global/tenant |
| communication.consent.transactional_required | boolean | global/tenant |
| communication.suppression_lists.enabled | boolean | global/tenant |

## 9. Quiet Hours Configuration

| Key | Type | Scope |
|---|---|---|
| communication.quiet_hours.enabled | boolean | global/tenant/user |
| communication.quiet_hours.start | time | tenant/user |
| communication.quiet_hours.end | time | tenant/user |
| communication.quiet_hours.timezone_mode | enum | global/tenant |
| communication.quiet_hours.critical_bypass_enabled | boolean | global/tenant |

## 10. Retry Configuration

| Key | Type | Scope |
|---|---|---|
| communication.retry.enabled | boolean | global/tenant |
| communication.retry.max_attempts | integer | global/tenant/channel |
| communication.retry.backoff_strategy | enum | global/tenant/channel |
| communication.retry.initial_delay_seconds | integer | global/tenant/channel |
| communication.retry.max_delay_seconds | integer | global/tenant/channel |

Backoff strategies:
- fixed
- linear
- exponential
- provider_recommended

## 11. Fallback and Escalation Configuration

| Key | Type | Scope |
|---|---|---|
| communication.fallback.enabled | boolean | global/tenant |
| communication.fallback.channel_order | list | tenant/rule |
| communication.escalation.enabled | boolean | global/tenant |
| communication.escalation.default_delay_minutes | integer | tenant/rule |
| communication.escalation.max_levels | integer | tenant/rule |

## 12. Inbox Configuration

| Key | Type | Scope |
|---|---|---|
| communication.inbox.enabled | boolean | global/tenant |
| communication.inbox.retention_days | integer | global/tenant |
| communication.inbox.allow_archive | boolean | tenant |
| communication.inbox.allow_delete_hide | boolean | tenant |
| communication.inbox.unread_badge_enabled | boolean | tenant |

## 13. Campaign Configuration

| Key | Type | Scope |
|---|---|---|
| communication.campaigns.enabled | boolean | global/tenant |
| communication.campaigns.require_approval | boolean | global/tenant |
| communication.campaigns.max_recipients_per_campaign | integer | global/tenant |
| communication.campaigns.rate_limit_per_minute | integer | global/tenant |
| communication.campaigns.marketing_opt_in_required | boolean | global/tenant |

## 14. Rate Limit Configuration

| Key | Type | Scope |
|---|---|---|
| communication.rate_limits.sms.per_recipient_per_day | integer | global/tenant |
| communication.rate_limits.email.per_recipient_per_day | integer | global/tenant |
| communication.rate_limits.push.per_recipient_per_day | integer | global/tenant |
| communication.rate_limits.provider.per_minute | integer | global/provider |

## 15. Configuration Invariants

- Critical audit cannot be disabled.
- Provider credentials must be encrypted.
- Tenant overrides cannot violate platform minimums.
- Marketing campaigns require consent controls.
- Mandatory transactional channels cannot be disabled by user preference unless platform policy allows fallback.
