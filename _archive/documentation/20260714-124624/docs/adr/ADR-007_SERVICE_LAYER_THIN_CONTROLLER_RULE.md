# ADR-007 — Service Layer Ownership & the Thin-Controller Rule

## Status

Accepted — established incrementally from Module 08 onward, formalized
and given an automated guardrail in Module 18.

## Context

By Module 17B, this codebase had 16 apps, each with a `services/`
package holding classmethod-only service classes, and a new `apps.api`
layer calling into them. Nothing had ever written down the rule
explicitly, but every module had converged on the same shape
independently: business logic lives in services; models hold data shape
and invariants (append-only guards, `save()`/`delete()` overrides); views
(now API views) do request parsing, permission checks, and response
shaping only.

The risk this ADR addresses: without a written rule and a check, the
"thin controller" property is only as durable as the next contributor's
memory of precedent. Module 17B already found and fixed one violation
during its own review cycle (a direct `Wallet.objects.filter(...).first()`
call inside `apps/api/views/wallet.py`, moved into
`WalletService.get_wallet_or_none()`) — proof the discipline needs an
enforced check, not just convention.

## Decision

1. **Services own all mutation.** A view/API view never calls
   `.objects.create()`, `.save()`, `.delete()`, `.update()`, or any
   multi-row `.filter()`/`.exclude()`/`.annotate()`/`.aggregate()`/
   `.all()` directly. The only ORM access permitted in
   `apps/api/views/*.py` is a single-row, tenant-scoped
   `.objects.get(id=..., tenant_id=...)` used to resolve a request-body
   ID into an object before handing it to a service call — see
   `docs/architecture/api-guidelines.md`.
2. **Read-only aggregation gets its own service, not inline ORM in the
   caller.** `apps.reporting`'s services are the reference example — a
   caller (today: `apps.api`) never writes the `aggregate()`/`annotate()`
   query itself.
3. **DTOs, not ORM objects, cross a service boundary for display/report
   purposes.** Frozen dataclasses (`apps.reporting.dto`,
   `apps.discovery.services.dto`, `apps.payments.services.dto
   .PaymentResult`, `apps.matching.services.eligibility.EligibilityResult`)
   — see `docs/architecture/service-layer-guidelines.md`.
4. **This is enforced by an automated guardrail**, not just documentation:
   `apps/kernel/tests/test_architecture_guardrails.py`
   (`ApiViewOrmDisciplineTest`) source-inspects every file in
   `apps/api/views/` and fails if it finds a forbidden ORM call pattern.

## Consequences

- The rule is conservative by design (source-text pattern matching, not a
  deep static analyzer) to avoid false positives — see the guardrail
  test's own docstring for exactly what it checks and why.
- Future API modules (a hypothetical "17C") inherit this rule
  automatically: any new view file added under `apps/api/views/` is
  covered by the same guardrail without needing to register itself
  anywhere.
- The rule does not (and should not) apply inside `apps.reporting`,
  `apps.discovery`, or any other app's own `services/` package — those
  are exactly where the ORM aggregation the rule keeps out of the API
  layer is supposed to live.
