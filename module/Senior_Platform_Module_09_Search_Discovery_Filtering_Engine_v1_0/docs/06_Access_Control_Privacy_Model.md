# 06 — Access Control & Privacy Model

## 1. Access control layers

Module 09 enforces access at five layers:

1. API endpoint permission;
2. surface permission;
3. index group permission;
4. document-level permission tags;
5. field-level redaction.

A result is visible only if all layers pass.

## 2. Actor contexts

Generic actor contexts:

- anonymous visitor;
- authenticated requester;
- authenticated provider;
- organization operator;
- tenant administrator;
- platform operator;
- platform administrator;
- support agent;
- system worker.

## 3. Permission tags

Documents must carry permission tags such as:

- public:read;
- requester:own_request_read;
- provider:eligible_request_discovery;
- organization:member_profile_read;
- organization:admin_profile_read;
- tenant:admin_read;
- platform:operator_read;
- support:case_lookup_read.

The actual authority source is Module 08. Module 09 only evaluates resolved permission grants.

## 4. Privacy redaction profiles

Redaction profiles define fields visible per actor and surface.

Example:

| Field | Public | Authenticated provider | Tenant admin |
|---|---:|---:|---:|
| display_title | yes | yes | yes |
| general_location_area | yes | yes | yes |
| precise_location | no | conditional | yes |
| contact_information | no | no | conditional |
| internal_notes | no | no | yes |
| trust_risk_flags | no | no | conditional |
| pricing_summary | conditional | conditional | yes |

## 5. Sensitive query handling

Free-text search queries may contain sensitive data. The engine must support:

- query hashing;
- optional redacted query storage;
- raw query suppression;
- configurable retention;
- PII detection hooks;
- sensitive-term blocklist;
- consent-aware analytics.

## 6. Anti-enumeration

Module 09 must prevent search from becoming a data exfiltration tool.

Controls:

- minimum facet bucket counts;
- max result window;
- rate limits;
- query complexity limits;
- fuzzy search restrictions;
- private field non-indexing;
- pagination cursor integrity;
- detection of systematic enumeration;
- actor risk scoring integration.

## 7. Right to suppression

If an upstream module emits a privacy withdrawal, profile hidden, deletion, compliance block, or tenant membership revocation event, Module 09 must suppress or delete affected documents according to policy.

Critical suppressions bypass normal queue priority.

## 8. Audit boundary

The engine logs policy decisions and security outcomes, but does not expose raw security rules to public users.
