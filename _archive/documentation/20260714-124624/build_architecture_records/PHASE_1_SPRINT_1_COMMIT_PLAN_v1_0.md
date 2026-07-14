# Phase 1 Sprint 1 — Commit Plan v1.0

**Date:** July 6, 2026
**Sprint:** 1 of 4 (Phase 1)
**Goal:** Establish the running platform foundation
**Commits:** 18 small, reviewable commits
**Rule:** Each commit must leave the project in a working state

---

## Commit 1 — Repository Structure

**Goal:** Create the base directory structure for the project without any code.

**Files to create:**
```
src/                          (empty, project root for production code)
src/apps/                     (Django apps directory)
src/apps/__init__.py
src/config/                   (Django project configuration)
src/config/__init__.py
src/templates/                (Django templates)
src/static/                   (Static files)
src/locale/                   (Translations)
src/requirements/             (Pip requirements split)
src/docker/                   (Docker files)
```

**What must NOT be included:** No Python code, no dependencies, no configuration.

**Acceptance criteria:**
- Directory structure exists
- All `__init__.py` files are empty
- No imports, no logic

**Commands to run:** `ls -la src/` — verify structure exists.

**Rollback note:** `git revert HEAD` — safe, no state to lose.

---

## Commit 2 — Python/Django Toolchain

**Goal:** Define Python version, dependencies, and tooling configuration.

**Files to create:**
```
src/pyproject.toml            (Project metadata, dependencies, tool config)
src/requirements/base.txt     (Core dependencies)
src/requirements/dev.txt      (Development dependencies)
src/requirements/test.txt     (Test dependencies)
src/requirements/prod.txt     (Production dependencies)
src/.python-version           (Python 3.12)
src/ruff.toml                 (Linter/formatter config)
```

**What must NOT be included:** No Django project, no models, no Docker.

**Acceptance criteria:**
- `pyproject.toml` is valid TOML
- All dependencies have version pins
- `ruff.toml` configured for Django conventions
- Python version specified as 3.12

**Commands to run:** `cd src && pip install -r requirements/dev.txt` (in a venv) — all packages install.

**Rollback note:** `git revert HEAD` — no runtime state.

---

## Commit 3 — Docker Infrastructure

**Goal:** Docker and Docker Compose configuration for local development.

**Files to create:**
```
src/docker/Dockerfile.dev     (Development image: Python 3.12 + system deps)
src/docker/entrypoint.sh      (Container entrypoint: wait for DB, run command)
src/docker-compose.yml        (Services: db, redis, web, celery, beat)
src/.env.example              (Environment variable template)
src/.dockerignore             (Exclude unnecessary files from build)
```

**What must NOT be included:** No Django project (web service will fail until Commit 4, that's OK). No production Dockerfile yet.

**Acceptance criteria:**
- `docker-compose.yml` defines: db (postgis:16-3.4), redis (7-alpine), web, celery, beat
- `.env.example` has all required variables with safe defaults
- `Dockerfile.dev` builds without error (Python + system deps only)
- `docker-compose build` succeeds

**Commands to run:** `cd src && docker-compose build` — images build successfully.

**Rollback note:** `git revert HEAD` — no persistent state created.

---

## Commit 4 — Django Project Scaffold

**Goal:** Create the minimal Django project that can boot.

**Files to create:**
```
src/manage.py
src/config/settings/__init__.py
src/config/settings/base.py   (Minimal: INSTALLED_APPS, basic config, no DB yet)
src/config/urls.py            (Empty URL conf)
src/config/wsgi.py
src/config/asgi.py
```

**What must NOT be included:** No database config, no Redis, no Celery, no custom user model yet.

**Acceptance criteria:**
- `python manage.py check` passes (with default SQLite for check only)
- No import errors
- INSTALLED_APPS includes only Django built-ins + rest_framework placeholder

**Commands to run:** `cd src && python manage.py check --settings=config.settings.base` — System check passes.

**Rollback note:** `git revert HEAD` — Django removed, back to toolchain only.

---

## Commit 5 — Settings Architecture

**Goal:** Split settings into base/development/testing/production with all environment-specific config.

**Files to create/change:**
```
src/config/settings/base.py       (Shared: apps, middleware, templates, i18n)
src/config/settings/development.py (DEBUG=True, console email, verbose logging)
src/config/settings/testing.py    (Fast tests: in-memory where possible)
src/config/settings/production.py (Security hardened, no DEBUG)
```

**What must NOT be included:** No database config yet (placeholder only), no Redis config yet.

**Acceptance criteria:**
- Each settings file imports from base
- `DJANGO_SETTINGS_MODULE` selects environment
- `python manage.py check --settings=config.settings.development` passes
- `python manage.py check --settings=config.settings.testing` passes

**Commands to run:** `python manage.py check` with each settings module.

**Rollback note:** Revert to single base.py state.

---

## Commit 6 — PostgreSQL/PostGIS Connection

**Goal:** Configure Django to connect to PostgreSQL with PostGIS support.

**Files to change:**
```
src/config/settings/base.py       (Add DATABASES config from env)
src/config/settings/development.py (Local DB settings)
src/config/settings/testing.py    (Test DB settings)
```

**What must NOT be included:** No models, no migrations, no schemas yet.

**Acceptance criteria:**
- `docker-compose up db` starts PostgreSQL
- `python manage.py check` passes with PostgreSQL configured
- PostGIS extension is available (verified via `SELECT PostGIS_Version()`)
- Database connection uses environment variables

**Commands to run:** `docker-compose up -d db && python manage.py check` — passes.

**Rollback note:** Remove DATABASES config, revert to SQLite placeholder.

---

## Commit 7 — Redis Connection

**Goal:** Configure Django to use Redis for caching.

**Files to change:**
```
src/config/settings/base.py       (Add CACHES config with Redis backend)
```

**What must NOT be included:** No Celery yet, no session storage changes.

**Acceptance criteria:**
- `docker-compose up -d redis` starts Redis
- Django cache operations work (set/get via `django.core.cache`)
- Cache backend configured from `REDIS_URL` environment variable

**Commands to run:** `docker-compose up -d redis && python manage.py shell -c "from django.core.cache import cache; cache.set('test', 1); assert cache.get('test') == 1; print('OK')"` — prints OK.

**Rollback note:** Remove CACHES config.

---

## Commit 8 — Celery Foundation

**Goal:** Configure Celery with Redis broker for background task processing.

**Files to create/change:**
```
src/config/celery.py              (Celery app configuration)
src/config/__init__.py            (Import celery app)
src/config/settings/base.py      (Add CELERY_* settings)
```

**What must NOT be included:** No tasks, no beat schedule, no workers running.

**Acceptance criteria:**
- Celery app instantiates without error
- `celery -A config inspect ping` responds (with worker running)
- Broker URL configured from environment variable
- Autodiscover configured for `apps.*` path

**Commands to run:** `celery -A config inspect ping` (with docker-compose services up) — responds with pong.

**Rollback note:** Remove celery.py and CELERY settings.

---

## Commit 9 — Logging and Correlation ID Foundation

**Goal:** Structured logging configuration and correlation ID middleware.

**Files to create/change:**
```
src/config/settings/base.py           (LOGGING dict config)
src/apps/kernel/__init__.py
src/apps/kernel/apps.py               (KernelConfig AppConfig)
src/apps/kernel/middleware/__init__.py
src/apps/kernel/middleware/correlation.py  (CorrelationMiddleware)
```

**What must NOT be included:** No tenant middleware yet, no audit logging.

**Acceptance criteria:**
- Structured JSON logging in production settings
- Console logging in development settings
- Every request gets `X-Correlation-ID` header (generated if not provided)
- Correlation ID included in log output
- Middleware registered in settings

**Commands to run:** `curl -v http://localhost:8000/` — response includes `X-Correlation-ID` header.

**Rollback note:** Remove middleware and LOGGING config.

---

## Commit 10 — Health Check Endpoint

**Goal:** A simple `/api/v1/health/` endpoint that verifies DB and Redis connectivity.

**Files to create/change:**
```
src/config/urls.py                    (Include kernel URLs)
src/apps/kernel/api/__init__.py
src/apps/kernel/api/urls.py
src/apps/kernel/api/health.py         (HealthCheckView)
```

**What must NOT be included:** No authentication, no DRF serializers, no models.

**Acceptance criteria:**
- `GET /api/v1/health/` returns 200 with `{"status": "healthy", "db": "ok", "redis": "ok"}`
- If DB is down, returns 503 with `{"status": "unhealthy", "db": "error", ...}`
- If Redis is down, returns 503 with `{"status": "unhealthy", "redis": "error", ...}`
- Response includes correlation ID

**Commands to run:** `curl http://localhost:8000/api/v1/health/` — returns 200 JSON.

**Rollback note:** Remove health endpoint and URL config.

---

## Commit 11 — CI Pipeline

**Goal:** GitHub Actions workflow for automated testing on push/PR.

**Files to create:**
```
src/.github/workflows/ci.yml         (Lint + test + type-check pipeline)
```

**What must NOT be included:** No deployment, no Docker image build, no CD.

**Acceptance criteria:**
- CI runs on push and pull_request events
- Services: PostgreSQL (postgis:16-3.4), Redis (7-alpine)
- Steps: checkout, setup-python, install deps, ruff check, ruff format --check, manage.py test
- Pipeline passes on current codebase

**Commands to run:** Push to branch → GitHub Actions runs → green check.

**Rollback note:** Remove workflow file.

---

## Commit 12 — PostgreSQL Schema Creation Migration

**Goal:** Create all 23 PostgreSQL schemas via initial migration.

**Files to create:**
```
src/apps/kernel/migrations/__init__.py
src/apps/kernel/migrations/0001_create_schemas.py   (RunSQL: CREATE SCHEMA IF NOT EXISTS ...)
```

**What must NOT be included:** No models, no tables — only schema creation.

**Acceptance criteria:**
- `python manage.py migrate` creates all 23 schemas
- Schemas verified: `SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('public', 'information_schema', 'pg_catalog', 'pg_toast');` returns 23 rows
- Migration is reversible (DROP SCHEMA IF EXISTS)
- No tables created yet

**Commands to run:** `python manage.py migrate && python manage.py dbshell -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'kernel';"` — returns 'kernel'.

**Rollback note:** `python manage.py migrate kernel zero` — drops schemas.

---

## Commit 13 — Kernel Base Models

**Goal:** Create abstract base classes that all future models inherit from.

**Files to create:**
```
src/apps/common/__init__.py
src/apps/common/models.py            (TenantAwareModel, SoftDeleteModel, TimestampedModel)
src/apps/common/managers.py          (ActiveManager, TenantScopedManager)
src/apps/common/enums.py             (Shared enums/choices)
src/apps/common/validators.py        (Common validators)
```

**What must NOT be included:** No concrete models, no migrations, no tables.

**Acceptance criteria:**
- TenantAwareModel is abstract (Meta: abstract = True)
- TenantAwareModel has: id (UUID), tenant (FK), created_at, updated_at, version, created_by, updated_by
- SoftDeleteModel adds: deleted_at, deleted_by, is_deleted property
- ActiveManager filters out soft-deleted records
- `python manage.py check` passes
- No migrations generated (all abstract)

**Commands to run:** `python manage.py check` — passes. `python manage.py makemigrations --check` — no new migrations.

**Rollback note:** Remove common/models.py.

---

## Commit 14 — Tenant Model

**Goal:** Create the Tenant concrete model — the root entity for multi-tenancy.

**Files to create/change:**
```
src/apps/kernel/models/__init__.py
src/apps/kernel/models/tenant.py     (Tenant model)
src/apps/kernel/migrations/0002_tenant.py  (Auto-generated migration)
```

**What must NOT be included:** No tenant middleware resolution yet (that was Commit 9 stub; full resolution comes with User model). No other models.

**Acceptance criteria:**
- Tenant model has: id (UUID PK), name, slug (unique), domain, status, settings (JSONB), metadata (JSONB), created_at, updated_at, version
- Table created in `kernel` schema: `db_table = 'kernel"."tenant'` (or via search_path)
- `python manage.py migrate` creates the table
- Tenant can be created via Django shell
- Slug uniqueness enforced at DB level

**Commands to run:** `python manage.py migrate && python manage.py shell -c "from apps.kernel.models import Tenant; t = Tenant.objects.create(name='Test', slug='test'); print(t.id)"` — prints UUID.

**Rollback note:** `python manage.py migrate kernel 0001` — removes tenant table.

---

## Commit 15 — Person and UserAccount Models

**Goal:** Create Person (stable identity) and UserAccount (authentication) as separate entities per ADR-001.01.

**Files to create/change:**
```
src/apps/kernel/models/user.py       (Person + UserAccount models)
src/apps/kernel/models/__init__.py   (Export new models)
src/apps/kernel/migrations/0003_person_user.py
src/config/settings/base.py          (AUTH_USER_MODEL = 'kernel.UserAccount')
```

**What must NOT be included:** No Credential model (Phase 2). No profile models. No auth backends.

**Acceptance criteria:**
- Person has: id (UUID), tenant (FK), full_name, status, metadata, created_at, updated_at, version
- UserAccount has: id (UUID), person (FK to Person), tenant (FK), email, phone, is_active, is_staff, date_joined
- UserAccount extends AbstractBaseUser
- AUTH_USER_MODEL points to UserAccount
- Person and UserAccount are in `kernel` schema
- One Person can have multiple UserAccounts (1:N FK)
- `python manage.py migrate` succeeds
- `python manage.py createsuperuser` works (for admin access)

**Commands to run:** `python manage.py migrate && python manage.py createsuperuser --email admin@test.com` — works.

**Rollback note:** `python manage.py migrate kernel 0002` — removes person/user tables. Must also revert AUTH_USER_MODEL.

---

## Commit 16 — RBAC Foundation

**Goal:** Create Role, Permission, and RoleAssignment models per ADR-001.13.

**Files to create/change:**
```
src/apps/kernel/models/rbac.py       (Role, Permission, RoleAssignment)
src/apps/kernel/models/__init__.py   (Export new models)
src/apps/kernel/migrations/0004_rbac.py
```

**What must NOT be included:** No permission evaluation engine (Phase 2). No permission checking middleware. No role seeding yet.

**Acceptance criteria:**
- Role: id (UUID), tenant (FK), name, slug, description, is_system, permissions (JSONB), metadata
- Permission: id (UUID), key (unique), module_id, resource_type, action, description, default_roles (JSONB), requires_scope, audit_required
- RoleAssignment: id (UUID), tenant (FK), user (FK to UserAccount), role (FK), scope_type, scope_id, is_active, granted_at, expires_at
- Role.slug is unique per tenant
- Permission.key is globally unique
- `python manage.py migrate` succeeds
- Models queryable via Django shell

**Commands to run:** `python manage.py migrate && python manage.py shell -c "from apps.kernel.models import Permission; Permission.objects.create(key='test.action', module_id='M25', resource_type='test', action='create'); print('OK')"` — prints OK.

**Rollback note:** `python manage.py migrate kernel 0003` — removes RBAC tables.

---

## Commit 17 — Seed Command and Admin Registration

**Goal:** Management command to seed dev tenant + default roles, and register all kernel models in Django admin.

**Files to create:**
```
src/apps/kernel/management/__init__.py
src/apps/kernel/management/commands/__init__.py
src/apps/kernel/management/commands/seed_tenant.py
src/apps/kernel/admin.py
```

**What must NOT be included:** No production data. No business module seeds. No configuration keys yet (Sprint 2).

**Acceptance criteria:**
- `python manage.py seed_tenant` creates: dev tenant, superuser, default platform roles (platform_owner, platform_team, customer, independent_provider, organization_owner, organization_staff, organization_provider)
- Command is idempotent (running twice doesn't duplicate)
- Django admin at `/admin/` shows: Tenant, Person, UserAccount, Role, Permission, RoleAssignment
- Admin is accessible with seeded superuser credentials

**Commands to run:** `python manage.py seed_tenant && python manage.py runserver` → navigate to `/admin/` → login → see all models.

**Rollback note:** `python manage.py flush` — removes seeded data (or revert migration).

---

## Commit 18 — Sprint 1 Verification Report

**Goal:** Run full verification of Sprint 1, document results, confirm all acceptance criteria pass.

**Files to create:**
```
src/SPRINT_1_VERIFICATION.md         (Verification results)
```

**What must NOT be included:** No new code. Only verification documentation.

**Acceptance criteria:**
- All 17 previous commits' acceptance criteria verified and documented
- `docker-compose up` starts in <60s ✓
- `python manage.py migrate` runs clean ✓
- `python manage.py test` passes (0 failures) ✓
- `ruff check .` passes ✓
- Health check returns 200 ✓
- Tenant model in kernel schema ✓
- Person ≠ UserAccount (separate tables, FK relationship) ✓
- RBAC models exist and are queryable ✓
- Correlation ID propagates ✓
- CI pipeline green ✓
- Django admin accessible with all models ✓
- Seed command idempotent ✓

**Commands to run:** Run all verification commands, document output.

**Rollback note:** Delete verification file — no code impact.

---

## Summary Table

| # | Commit | Creates Tables? | Creates APIs? | Creates Models? |
|---|--------|----------------|---------------|-----------------|
| 1 | Repository structure | No | No | No |
| 2 | Python toolchain | No | No | No |
| 3 | Docker | No | No | No |
| 4 | Django scaffold | No | No | No |
| 5 | Settings | No | No | No |
| 6 | PostgreSQL | No | No | No |
| 7 | Redis | No | No | No |
| 8 | Celery | No | No | No |
| 9 | Logging + Correlation | No | No | No (middleware only) |
| 10 | Health check | No | Yes (1 endpoint) | No |
| 11 | CI pipeline | No | No | No |
| 12 | Schema migration | No tables (schemas only) | No | No |
| 13 | Base models | No (abstract) | No | Abstract only |
| 14 | Tenant | Yes (1 table) | No | Yes (1 concrete) |
| 15 | Person + UserAccount | Yes (2 tables) | No | Yes (2 concrete) |
| 16 | RBAC | Yes (3 tables) | No | Yes (3 concrete) |
| 17 | Seed + Admin | No new tables | No | No |
| 18 | Verification | No | No | No |

**Total new tables created in Sprint 1:** 6 (Tenant, Person, UserAccount, Role, Permission, RoleAssignment)

**All tables live in `kernel` schema — no other schema is populated until Sprint 2+.**

---

*End of Phase 1 Sprint 1 Commit Plan v1.0*
