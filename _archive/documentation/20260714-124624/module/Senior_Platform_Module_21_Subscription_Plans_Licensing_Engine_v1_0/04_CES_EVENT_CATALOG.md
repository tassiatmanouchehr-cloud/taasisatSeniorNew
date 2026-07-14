# Senior Platform — Module 21 — Subscription, Plans & Licensing Engine v1.0

**Status:** Frozen Draft / Enterprise Package v1.0  
**Domain:** Generic Service Marketplace Framework  
**Zero-domain-leakage:** Mandatory  
**Multi-tenant boundary:** Mandatory  

Plans, quotas, entitlements, usage metering, billing integration, upgrades, downgrades, trials and license governance.

---

## Event Envelope Required Fields
`event_id`, `event_name`, `event_version`, `occurred_at`, `tenant_id`, `actor_id`, `actor_type`, `source_module`, `correlation_id`, `causation_id`, `idempotency_key`, `payload`, `metadata`.

## Events
### `SubscriptionPlansLicensingCreated`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionPlansLicensingUpdated`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionPlansLicensingActivated`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionPlansLicensingDeactivated`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionPlansLicensingEvaluationRequested`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionPlansLicensingEvaluationCompleted`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionPlansLicensingPolicyApplied`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionPlansLicensingPolicyRejected`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionPlansLicensingPermissionDenied`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionPlansLicensingAuditRecorded`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionPlansLicensingErrorRaised`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionPlansLicensingRetryScheduled`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionPlansLicensingExpired`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionPlansLicensingArchived`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `PlanCreated`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionStarted`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `EntitlementGranted`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `QuotaExceeded`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.

### `SubscriptionCancelled`
- Type: domain fact.
- Version: 1.0.
- Consumers: audit, reporting, workflow, integration gateway and dependent modules.
- Compatibility: additive changes only; breaking changes require new event version.
