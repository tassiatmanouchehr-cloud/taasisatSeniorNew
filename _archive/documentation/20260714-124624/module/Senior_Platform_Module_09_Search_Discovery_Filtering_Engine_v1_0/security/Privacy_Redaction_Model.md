# Privacy Redaction Model

## Redaction sequence

1. Retrieve candidate documents.
2. Apply document-level policy.
3. Resolve redaction profile.
4. Remove prohibited fields.
5. Transform precision-sensitive fields.
6. Validate response schema.
7. Fail closed on redaction error.

## Field precision examples

| Field | Public handling | Private handling |
|---|---|---|
| location | area or approximate | precise only if permitted |
| price | range only | exact summary if permitted |
| availability | coarse windows | exact slots if permitted |
| contact | never | only through authorized workflow |
| internal notes | never | admin only |
| risk flags | never | restricted admin/security only |

## Query privacy

Raw query text is not retained by default. Query hash and redacted text may be retained according to CCS.
