# Access Policies

## Default Policy
Deny by default. Allow only when a policy explicitly grants the actor capability within scope.

## Scope Types
- Platform
- Tenant
- Organization
- Department
- Actor-owned resource
- Order/resource-scoped grant
- Temporary emergency scope

## Authentication Boundary
Authentication proves account/session validity. It does not authorize marketplace actions. Every protected action still requires authorization.

## Authorization Boundary
Authorization must include actor context, tenant, resource, requested action, session/device assurance, verification state and governance restrictions.

## Tenant Boundary
No tenant actor can access another tenant's private data without explicit cross-tenant platform permission.

## Provider Boundary
A provider may have independent context and organization-affiliated context. These contexts must remain separate for permissions, visibility, statistics and financial access unless a policy explicitly merges display data.

## Staff Boundary
Organization staff permissions are bounded by organization, department and assigned role. Staff cannot self-escalate.

## Platform Team Boundary
Platform team permissions must be granular. Critical actions require MFA, reason capture, elevated audit and optional approval.

## Financial Visibility Boundary
Financial data access must be delegated by Module 05 policy and enforced through Module 08 permissions. Trusted persons never receive financial-history access by default.

## Profile Visibility Boundary
Profile fields are served only after Profile Service visibility evaluation.

## Verification Gate Policy
Certain capabilities may require verification, such as public profile publishing, provider activation, organization activation, financial operations, or accepting service assignments.

## Revocation Policy
Permissions and grants can be revoked by authorized actors, automated risk processes, expiry, organization removal, account closure, or governance sanctions.
