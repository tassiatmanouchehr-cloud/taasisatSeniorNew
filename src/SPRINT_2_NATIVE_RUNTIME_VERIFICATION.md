# Sprint 2 Native Runtime Verification

## Enterprise Service Marketplace Platform — Phase 1, Sprint 2

**Date:** July 6, 2026
**Purpose:** Prove the Platform Kernel runs in a native Python environment
**Blocking Gate:** Sprint 3 cannot begin until STATUS: PASS

---

## ⚠️ EXECUTION ENVIRONMENT LIMITATION

**This verification could NOT be completed in the Kiro sandbox.**

**Reason:** The sandbox operates in `INTEGRATIONS_ONLY` network mode — no access to PyPI, no pip install possible. Django and all project dependencies cannot be installed.

**Required:** The project owner must execute these steps in their local Windows/WSL/Linux environment with:
- Python 3.12+
- PostgreSQL 16+ (native installation)
- Redis (optional — app falls back to LocMem cache)
- Network access to PyPI

---

## Step-by-Step Execution Script

Copy and execute the following commands in your local environment:

### Step 1 — Python Environment

```bash
cd /path/to/Senior1/src

python --version
# Expected: Python 3.12.x

python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements/dev.txt
```

**Expected result:** All packages install successfully. Key packages:
- django >= 5.1
- djangorestframework >= 3.15
- psycopg[binary] >= 3.1
- celery[redis] >= 5.4
- jdatetime >= 5.0

---

### Step 2 — Django Validation

Set environment variables for native mode:
```bash
# Linux/Mac:
export GIS_ENABLED=false
export DJANGO_SETTINGS_MODULE=config.settings.development
export SECRET_KEY=dev-runtime-validation-key

# Windows PowerShell:
$env:GIS_ENABLED="false"
$env:DJANGO_SETTINGS_MODULE="config.settings.development"
$env:SECRET_KEY="dev-runtime-validation-key"
```

Then run:
```bash
python manage.py check
```

**Expected result:**
```
System check identified no issues.
```

---

### Step 3 — PostgreSQL Setup

Before migrations, ensure PostgreSQL is running and the database exists:

```bash
# Create database (adjust credentials as needed):
psql -U postgres -c "CREATE USER marketplace WITH PASSWORD 'marketplace';"
psql -U postgres -c "CREATE DATABASE marketplace OWNER marketplace;"
psql -U postgres -c "ALTER USER marketplace CREATEDB;"  # For test DB creation

# If using PostGIS:
psql -U postgres -d marketplace -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

Set environment variables:
```bash
export DJANGO_SETTINGS_MODULE=config.settings.development
export GIS_ENABLED=false
export DATABASE_NAME=marketplace
export DATABASE_USER=marketplace
export DATABASE_PASSWORD=marketplace
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export SECRET_KEY=dev-runtime-validation-key
```

**Alternative (without PostGIS):** If PostGIS is not installed, set:
```bash
export DATABASE_ENGINE=django.db.backends.postgresql
```
And remove `django.contrib.gis` from INSTALLED_APPS temporarily.

---

### Step 4 — Migration Validation

```bash
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py showmigrations
```

**Expected result:**
- `makemigrations --check` reports no new migrations needed (or may detect drift from hand-written migrations — see Fixes section)
- `migrate` creates all 14 kernel tables in the correct schemas
- `showmigrations` shows all 10 kernel migrations applied

**Likely fix needed:** Hand-written migrations (0002-0010) may not exactly match what `makemigrations` would generate. If `makemigrations --check` reports pending changes:

```bash
# Generate Django's version of the migrations:
python manage.py makemigrations kernel

# Then compare with the hand-written ones and resolve differences
```

---

### Step 5 — Test Suite

```bash
python manage.py test apps.kernel --verbosity=2
```

**Expected result:** 49 tests pass.

**If using SQLite for tests:**
```bash
USE_SQLITE=1 python manage.py test apps.kernel --settings=config.settings.testing --verbosity=2
```

**Note:** SQLite tests will skip schema-prefixed table tests. Full validation requires PostgreSQL.

---

### Step 6 — Seed Validation

```bash
python manage.py seed_tenant
```

**Expected result:**
```
Created tenant: Development Tenant (dev)
Roles: 14 created, 0 already existed
Created person: Platform Administrator
Created superuser: admin@marketplace.local

Seed complete. You can now log into /admin/ with:
  Email: admin@marketplace.local
  Password: admin123456
```

---

### Step 7 — Application Startup

```bash
python manage.py runserver
```

**Expected result:**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
July 06, 2026 - XX:XX:XX
Django version 5.X.X, using settings 'config.settings.development'
Starting development server at http://127.0.0.1:8000/
```

---

### Step 8 — Health Endpoint

In a separate terminal:
```bash
curl http://localhost:8000/api/v1/health/
```

**Expected result:**
```json
{"status": "healthy", "db": "ok", "cache": "ok", "correlation_id": "..."}
```

If Redis is not available, cache will report "ok" (using LocMem fallback).

---

### Step 9 — Admin Access

Open browser: `http://localhost:8000/admin/`

Login with:
- Email: `admin@marketplace.local`
- Password: `admin123456`

**Expected:** Django admin dashboard showing all kernel models:
- Tenants
- Persons
- User Accounts
- Roles
- Permissions
- Role Assignments

---

## Known Issues & Fixes

### Issue 1: GDAL/PostGIS Not Available on Native Windows (FIXED)

**Problem:** Even with `DATABASE_ENGINE=django.db.backends.postgresql`, Django still loaded `django.contrib.gis` from `INSTALLED_APPS`, which requires the GDAL library. On native Windows development, GDAL is not typically installed.

**Root cause:** `django.contrib.gis` was unconditionally included in `INSTALLED_APPS` regardless of the database engine setting.

**Fix applied:** Added `GIS_ENABLED` environment variable flag:
- `GIS_ENABLED=false` (default for native dev): `django.contrib.gis` NOT in `INSTALLED_APPS`, database engine defaults to `django.db.backends.postgresql`
- `GIS_ENABLED=true` (Docker/production): `django.contrib.gis` added to `INSTALLED_APPS`, database engine defaults to `django.contrib.gis.db.backends.postgis`

**Files changed:** `config/settings/base.py`, `.env.example`

**Validation commands (PowerShell):**
```powershell
$env:GIS_ENABLED="false"
$env:DATABASE_ENGINE="django.db.backends.postgresql"
python manage.py check
# Expected: System check identified no issues.
```

**Validation commands (bash):**
```bash
export GIS_ENABLED=false
export DATABASE_ENGINE=django.db.backends.postgresql
python manage.py check
# Expected: System check identified no issues.
```

### Issue 2: `db_table` with Schema Prefix

Django uses `db_table = 'kernel"."table_name'` to create tables in the `kernel` schema. This requires the schema to exist first (created by migration 0001).

**Fix if schema creation fails:** Ensure migration 0001_create_schemas runs before any model migration. If PostgreSQL user lacks schema creation privileges:
```sql
GRANT CREATE ON DATABASE marketplace TO marketplace;
```

### Issue 2: Hand-Written Migrations vs. makemigrations

The Sprint 2 migrations (0005-0010) were hand-written to match the model definitions. Django's `makemigrations` may generate slightly different migration code (field ordering, manager references, etc.).

**Fix:** If `makemigrations --check` detects drift:
1. Delete hand-written migrations 0005-0010
2. Run `python manage.py makemigrations kernel`
3. Verify the generated migrations create the correct tables
4. Commit the corrected migrations

### Issue 3: UserAccountManager in Migration

The migration for UserAccount (0003) references `django.contrib.auth.models.UserManager` instead of the custom `UserAccountManager`. This may cause a warning but should not prevent migration.

**Fix if needed:** Update migration 0003 to reference the correct manager path.

### Issue 4: PostGIS Not Available

If PostGIS extension is not installed on the PostgreSQL server:

**Fix:** Set environment variable:
```bash
export DATABASE_ENGINE=django.db.backends.postgresql
```

And remove `"django.contrib.gis"` from `INSTALLED_APPS` in `config/settings/base.py`.

This is a temporary fix for validation only. PostGIS will be required for Module 10 (Geospatial).

### Issue 5: Celery Import on Startup

`config/__init__.py` imports `celery_app` from `config/celery.py`. If Celery fails to import (e.g., broker connection error), Django won't start.

**Fix:** Celery handles missing broker gracefully at import time. If it doesn't, temporarily modify `config/__init__.py`:
```python
try:
    from .celery import app as celery_app
    __all__ = ("celery_app",)
except ImportError:
    celery_app = None
    __all__ = ()
```

---

## Native Compatibility Checklist

| # | Requirement | Status |
|---|------------|--------|
| 1 | No Docker dependency in application code | ✅ Verified (grep confirms no docker references in apps/) |
| 2 | No hardcoded paths | ✅ All paths via BASE_DIR + Path |
| 3 | No hardcoded credentials | ✅ All from os.environ.get() |
| 4 | No hardcoded ports | ✅ DATABASE_PORT from env |
| 5 | Environment-variable based configuration | ✅ All settings from env vars |
| 6 | Architecture compliant with ADR documents | ✅ No violations detected |
| 7 | Settings support native Python execution | ✅ REDIS_URL fallback to LocMem, DATABASE_ENGINE configurable |
| 8 | Tests can run without Docker | ✅ USE_SQLITE=1 for unit tests, CELERY_TASK_ALWAYS_EAGER |

---

## Pre-Validation Results (Syntax/Static Only)

These checks CAN be performed in the sandbox:

| Check | Result |
|-------|--------|
| Python files syntax (ast.parse) | ✅ 49/49 files pass |
| Migration dependency chain | ✅ 0001→0002→...→0010 correct |
| All models have db_table in kernel schema | ✅ Confirmed |
| ADR compliance | ✅ No violations |
| No Docker references in app code | ✅ Confirmed |
| All config from environment variables | ✅ Confirmed |
| Test methods defined | ✅ 49 methods across 5 files |

---

## Final Status

```
Sprint 2 Runtime Verification

STATUS: PENDING — Requires local execution by project owner

Reason: Kiro sandbox has INTEGRATIONS_ONLY network mode.
        Cannot install Django or any Python packages.
        Cannot run PostgreSQL or Redis.
        Cannot execute manage.py commands.

Action Required: Execute Steps 1-9 in local environment.
                 Report results back for Sprint 3 gate approval.
```

---

## Quick Validation Script

Save this as `validate_sprint2.sh` and run in your local environment:

```bash
#!/bin/bash
set -e

echo "=== Sprint 2 Native Runtime Validation ==="
echo ""

# Step 1
echo "--- Step 1: Environment ---"
python --version
pip --version

# Step 2
echo ""
echo "--- Step 2: Django Check ---"
python manage.py check

# Step 3
echo ""
echo "--- Step 3: Migrations ---"
python manage.py migrate --run-syncdb
python manage.py showmigrations kernel

# Step 4
echo ""
echo "--- Step 4: Database ---"
python manage.py dbshell <<EOF
SELECT schemaname, count(*) as table_count 
FROM pg_tables 
WHERE schemaname = 'kernel' 
GROUP BY schemaname;
EOF

# Step 5
echo ""
echo "--- Step 5: Tests ---"
python manage.py test apps.kernel --verbosity=2

# Step 6
echo ""
echo "--- Step 6: Seed ---"
python manage.py seed_tenant

# Step 7 & 8
echo ""
echo "--- Step 7 & 8: Server + Health ---"
python manage.py runserver &
SERVER_PID=$!
sleep 3
curl -s http://localhost:8000/api/v1/health/ | python -m json.tool
kill $SERVER_PID

echo ""
echo "=== ALL STEPS PASSED ==="
echo "Sprint 2 Runtime Verification: STATUS: PASS"
```

---

*End of Sprint 2 Native Runtime Verification Document*
