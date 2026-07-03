# Reference Implementation Mapping — Generic Framework to Generic Service Marketplace-Care Platform

This file is intentionally isolated from the framework core. It explains how a reference-implementation marketplace may map its domain terms onto generic Module 08 concepts without contaminating the reusable framework.

## Mapping
- Platform owner → `PLATFORM_OWNER`
- Platform support/marketing/security/IT/accounting team → `PLATFORM_TEAM_MEMBER`
- Provider company → `ORGANIZATION`
- Company admin/operator → `ORGANIZATION_STAFF`
- Independent provider/provider → `INDEPENDENT_PROVIDER`
- Company-affiliated provider/provider → `ORGANIZATION_PROVIDER`
- Customer or customer's family → `CUSTOMER`
- Customer trusted family/contact for one order → `TRUSTED_PERSON`

## Important Rule
The core framework must use only generic names. Domain labels may appear in translation files, UI labels, tenant configuration, onboarding copy, or reference implementation documentation, not in core entities, permission keys or event types.

## Example Affiliation Flow
A provider registers as independent. If they enter a provider-company identifier, an affiliation request is created. The company administrator must approve. If approved, the provider receives organization-provider context for that company; otherwise, the provider remains independent.

## Example Trusted Person Flow
A customer invites a trusted family member for one order. The trusted person can see progress and receive order communications, but cannot access customer account settings, financial history or other orders.
