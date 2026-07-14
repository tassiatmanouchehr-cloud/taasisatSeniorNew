# API Guidelines

Status: current as of Module 18. Covers `apps.api` (Modules 17A/17B).
See ADR-003 for why DRF and not a hand-rolled JSON layer.

## Structure

```
apps/api/
  urls.py                # the single /api/v1/ router — every route lives here
  permission_keys.py      # named RBAC permission_key constants
  permissions.py           # require_authenticated / resolve_tenant_id / require_permission / resolve_customer_profile
  pagination.py             # paginate() / parse_pagination_params() / Page DTO
  errors.py                  # ApiError — the API layer's own exception type
  exception_handler.py        # the DRF EXCEPTION_HANDLER — maps every exception to the error envelope
  serializers/
    <domain>.py                # one file per domain area, transport shape only
  views/
    base.py                     # ApiView(APIView), permission_classes = [AllowAny]
    <domain>.py                  # one file per domain area
```

## The thin-controller rule

Every view method does, in order:

1. `require_permission(request, <PERMISSION_KEY>)` (or
   `require_authenticated` alone for the fake-callback webhook) — this
   authenticates, derives `tenant_id` from `request.user.tenant_id`
   (**never** from the request body or URL), and enforces RBAC.
2. Validate the request body with a `Serializer` (shape only — no domain
   rules; those live in the service).
3. At most, resolve request-supplied IDs into tenant-scoped ORM objects
   via a single `.objects.get(id=..., tenant_id=tenant_id)` — never
   `.filter()`, `.exclude()`, `.annotate()`, `.aggregate()`, or `.all()`.
4. Call exactly one domain service method.
5. Serialize the result and return a `Response`.

No view contains a loop, a conditional business rule, or a multi-row
query. If you find yourself writing one, that logic belongs in the
service layer, not the view. This is enforced by an automated guardrail
— see `apps/kernel/tests/test_architecture_guardrails.py`
(`ApiViewOrmDisciplineTest`).

## `permission_classes = [AllowAny]` is deliberate

DRF's own permission framework is bypassed on purpose. `apps.api
.permissions.require_permission()` reuses `apps.kernel.services
.permission_service.PermissionService` directly — the platform's one and
only RBAC evaluator (Module 08). Wiring a second, DRF-native permission
system alongside it would create two sources of truth for authorization.
The one exception is `FakeProviderCallbackView`, which calls neither —
see `wallet-finance-boundary.md`'s sibling note in the payments views
module docstring for why (it simulates an unauthenticated PSP webhook).

## Error envelope

Every error response has the shape:

```json
{"error": {"code": "...", "message": "...", "details": {}}}
```

Wired via `settings.REST_FRAMEWORK["EXCEPTION_HANDLER"]`. Mapping, in
order:

1. `apps.api.errors.ApiError` → its own `code`/`status_code`/`details`.
2. A small, explicit allowlist of per-module domain exceptions
   (`DiscoveryError`, `PricingError`, `ReviewError`, `WalletError`,
   `PaymentError`) → `400 domain_error`, using the exception's own
   message (every module's `XError` message is already safe/human-written
   by convention — see `service-layer-guidelines.md`).
3. `apps.kernel.services.errors.PermissionDenied` → `403 permission_denied`.
4. `Http404`/`ObjectDoesNotExist` → `404 not_found`.
5. Anything DRF's own default handler recognizes (validation errors,
   method-not-allowed, etc.) → reshaped into the same envelope.
6. Anything else → `500 internal_error`, logged server-side via
   `logger.exception(...)`, **never** the exception's message or a
   traceback in the response body.

**Note**: step 2's allowlist only covers the five modules this API
surface currently exposes. Adding a new domain's endpoints in a future
module means adding that module's `XError` to the allowlist — it will
not be picked up automatically (deliberately explicit, not magic).

## Permission-key naming

See `rbac-permissions.md`.

## Pagination

`apps.api.pagination.paginate(items, *, limit, offset)` — `DEFAULT_LIMIT
= 20`, `MAX_LIMIT = 100`. Works over both plain sequences (`len()`) and
Django `QuerySet`s (`.count()` + real `LIMIT`/`OFFSET` slicing — checked
via `isinstance(items, QuerySet)`, not duck-typing, because `list.count()`
and `QuerySet.count()` have incompatible signatures). Every paginated
response has the shape `{"results": [...], "limit", "offset",
"total_count", "has_more"}`.

## Versioning

Every route lives under `/api/v1/`. There is no unversioned route, and a
guardrail test (`apps/api/tests/test_urls.py`) asserts several paths 404
outside that prefix.

## Serializers are transport-only

`rest_framework.serializers.Serializer` (never `ModelSerializer`) for
every response shape — most of what's serialized is a frozen dataclass
DTO or a plain dict (reporting/reputation/wallet-balance), not always an
ORM instance. Request-body serializers validate types/presence/bounds
only; every domain rule (rating bounds, amount validation, state
transitions) stays in the service that's called afterward. No serializer
in this codebase calls `.save()`.

## What's deferred (see `technical-debt-register.md` for detail)

- A single shared `ApiView` base class exists, but per-domain views don't
  yet share request-parsing helpers beyond `pagination.py`/`permissions
  .py` — some structural duplication across `views/*.py` remains.
- OpenAPI/schema generation (`drf-spectacular` is a declared dependency
  but unused).
- Real PSP signature/HMAC verification on the payments callback endpoint.
