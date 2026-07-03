# CCS Configuration Naming Standard v1.0

## Format

`module.group.setting`

Examples:

- `request.creation.requires_customer_identity`
- `request.approval.operator_review_required`
- `matching.ranking.max_candidates`
- `matching.response.timeout_minutes`
- `booking.assignment.auto_accept_enabled`
- `booking.lock.ttl_minutes`
- `execution.presence.gps_required`
- `execution.completion.customer_confirmation_required`
- `financial.wallet.enabled`
- `financial.settlement.hold_days`
- `trust.review.enabled`
- `trust.dispute.appeal_allowed`
- `communication.sms.enabled`
- `communication.template.approval_required`
- `identity.mfa.required_for_critical_actions`
- `identity.provider_affiliation.company_approval_required`

## Rules

1. Configuration must be tenant-aware unless explicitly platform-global.
2. Configuration must define type, default, scope, owner module, validation rule and audit behavior.
3. Sensitive configuration values must be secret-managed.
4. No module may introduce ad-hoc settings outside CCS.
