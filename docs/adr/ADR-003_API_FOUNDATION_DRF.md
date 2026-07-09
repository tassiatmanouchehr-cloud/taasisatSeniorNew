# ADR-003 — API Foundation on Django REST Framework

## Status

Accepted — Module 17A, corrected mid-module, reaffirmed in Module 18.

## Context

Before Module 17A, the only API surface was a single unauthenticated
health-check view (`apps/kernel/api/health.py`, plain Django `View` +
`JsonResponse`, mounted at `/api/v1/health/`, never tested). No
authenticated API pattern, no error envelope, no pagination convention
existed anywhere in the codebase.

Module 17A's initial Phase 1 inspection checked `pyproject.toml` for a
`djangorestframework` dependency, found none, and concluded DRF was only
an accidental/transitive install — building the foundation on it would be
undeclared-dependency risk. A minimal hand-rolled Django-`View` +
`JsonResponse` foundation was built instead, with DRF documented as
deferred.

This was wrong. `pyproject.toml` in this repository has no
`[project.dependencies]` section at all — it's tooling config (ruff,
pytest) only. The project's real dependency manifest is
`requirements/base.txt`, which the initial inspection never checked. It
declares `djangorestframework>=3.15,<4.0` as a first-class, intentional
dependency — alongside `drf-spectacular` (OpenAPI) and
`djangorestframework-simplejwt`, both also genuinely installed. The user
caught this and requested the rebuild; the correction was not a
preference change, it was fixing an incomplete inspection.

## Decision

Rebuild the API foundation on DRF:

- `rest_framework` registered in `INSTALLED_APPS`.
- Every view is a `rest_framework.views.APIView` subclass
  (`apps.api.views.base.ApiView`), returning `rest_framework.response
  .Response`.
- `settings.REST_FRAMEWORK["EXCEPTION_HANDLER"]` points at
  `apps.api.exception_handler.api_exception_handler` — DRF's own
  `dispatch()`/`handle_exception()` machinery does the routing; no custom
  `dispatch()` override is needed (contrast with the original hand-rolled
  version).
- `DEFAULT_PERMISSION_CLASSES = [AllowAny]` — DRF's own permission
  framework is deliberately bypassed; `apps.api.permissions
  .require_permission()` reuses `PermissionService` (Module 08) directly.
  See `docs/architecture/api-guidelines.md`.
- `DEFAULT_AUTHENTICATION_CLASSES = [SessionAuthentication]` — reuses the
  existing session login flow. No second authentication system.
- Serializers use plain `rest_framework.serializers.Serializer`, never
  `ModelSerializer` — most response data is a frozen-dataclass DTO or a
  plain dict, not always an ORM instance.
- `drf-spectacular`/OpenAPI schema generation remains genuinely deferred
  (unlike the DRF decision, this one still holds — see
  `docs/architecture/technical-debt-register.md`), since it's additive
  and not blocking anything.

## Consequences

- The health endpoint (`apps/kernel/api/health.py`) was **not** converted
  to DRF — it predates this module, has its own tests now (added in
  17A), and converting it wasn't part of "rebuild the custom foundation."
  It's reused as-is, routed through `apps.api.urls`.
- `config/urls.py`'s `/api/v1/` mount now points at `apps.api.urls`
  instead of the old `apps.kernel.api.urls` — a single canonical
  entrypoint.
- Every exception a view can raise funnels through one function
  (`api_exception_handler`), making the error envelope
  (`{"error": {"code", "message", "details"}}`) structurally guaranteed
  rather than convention-enforced.

## Lesson for future architecture decisions in this repository

**Check `requirements/*.txt`, not just `pyproject.toml`, before concluding
a dependency is unavailable or undeclared.** This repository keeps
dependency declarations and tooling config in separate files.
