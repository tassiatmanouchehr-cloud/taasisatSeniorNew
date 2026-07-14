# Policy Engine Specification

## Policy Structure
A policy contains:
- identity: policy_id, version, tenant_id, campaign_id
- scope: roles, segments, regions, services, categories, tenants, companies
- triggers: events, API calls, scheduled jobs
- eligibility predicates
- reward calculation formula
- caps and limits
- stacking and conflict rules
- fraud gates
- settlement criteria
- reversal criteria
- audit labels and reason code mappings

## Expression Model
Policies support nested logical expressions:
- AND
- OR
- NOT
- comparison operators
- date and duration operators
- count windows
- monetary thresholds
- geography predicates
- identity verification predicates
- trust/risk predicates

## Versioning
Published policies are immutable. Editing a live policy creates a new version. Evaluations always store policy_id and policy_version.

## Conflict Resolution
Supported modes:
- highest benefit wins
- platform lowest cost wins
- priority order
- stackable
- mutually exclusive
- manual review required
- finance approval required
