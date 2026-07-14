# 10 — Failure, Recovery & Degradation

## 1. Failure classes

| Failure | Required behavior |
|---|---|
| search provider unavailable | return controlled error or fallback query path |
| index lag high | display stale-data indicator or restrict surfaces |
| critical suppression lag | enter safe mode for affected surfaces |
| permission resolver unavailable | deny private search, allow only public cached discovery if configured |
| redaction failure | fail closed |
| facet timeout | return results without facets when allowed |
| autocomplete timeout | return no suggestions |
| saved search evaluator failure | retry and audit failure |
| reindex alias switch failure | rollback to previous index alias |

## 2. Safe mode

Safe mode may:

- disable private request discovery;
- disable cross-tenant search;
- disable autocomplete;
- disable facets with low bucket counts;
- limit result fields;
- force source-of-truth validation for selected results;
- show degraded status to admins.

## 3. Fallback query path

For small deployments, a fallback database query may be configured for limited administrative search. It must enforce the same permission and redaction rules.

Fallback is not allowed to bypass tenant isolation.

## 4. Data loss recovery

Search index can always be rebuilt from canonical modules and event logs. Module 09 must not hold irreplaceable business truth except saved searches, ranking profile overrides, facet definitions, and audit logs.

## 5. Disaster recovery

Required capabilities:

- backup saved searches;
- backup configuration;
- backup audit logs;
- restore index from canonical projections;
- rebuild per tenant;
- replay failed index operations;
- verify document counts and checksums.

## 6. Failure communication

Module 09 emits events for operational failures. Module 07 may notify administrators or operators. Module 09 does not send notifications directly.
