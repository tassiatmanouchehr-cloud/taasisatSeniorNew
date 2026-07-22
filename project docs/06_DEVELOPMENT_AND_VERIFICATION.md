# DEVELOPMENT AND VERIFICATION

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.12+ | Required by `pyproject.toml` |
| PostgreSQL | 16 | PostGIS optional (set `GIS_ENABLED=false` without it) |
| Node.js | 22 | For Tailwind CSS and Alpine.js build |
| npm | (bundled with Node) | — |

## Repository Clone

```bash
git clone https://github.com/tassiatmanouchehr-cloud/taasisatSeniorNew.git
cd taasisatSeniorNew/src
```

## Dependency Installation

### Python

```bash
python -m pip install -r requirements/base.txt   # production deps
python -m pip install -r requirements/dev.txt    # + dev tools (ruff, etc.)
python -m pip install -r requirements/test.txt   # + test deps (Playwright, etc.)
```

### Node (for CSS/JS build)

```bash
npm install
```

## Environment Configuration

Copy the example and adjust:

```bash
cp .env.example .env
```

### Critical `.env` variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_HOST` | localhost | PostgreSQL host |
| `DATABASE_PORT` | 5433 | PostgreSQL port (adjust to your install) |
| `DATABASE_NAME` | marketplace | Database name |
| `DATABASE_USER` | marketplace | Database role |
| `DATABASE_PASSWORD` | marketplace | Role password |
| `GIS_ENABLED` | false | Set `true` only with PostGIS + GDAL installed |
| `SECRET_KEY` | dev-only-insecure | Change in production |
| `DEBUG` | True | Never True in production |
| `PUBLIC_SITE_TENANT_SLUG` | (unset) | Optional: force public site to specific tenant |

### Database Creation (one-time)

PostgreSQL does not automatically create the `marketplace` role/database:

```bash
# Linux/Mac:
psql -U postgres -c "CREATE ROLE marketplace LOGIN PASSWORD 'marketplace' CREATEDB;"
psql -U postgres -c "CREATE DATABASE marketplace OWNER marketplace;"

# Windows PowerShell (adjust port if not 5432):
psql -U postgres -p 5433 -c "CREATE ROLE marketplace LOGIN PASSWORD 'marketplace' CREATEDB;"
psql -U postgres -p 5433 -c "CREATE DATABASE marketplace OWNER marketplace;"
```

`CREATEDB` is required because `manage.py test` creates/destroys its own test database.

## Migration

```bash
python manage.py migrate
```

## Seed Data

```bash
python manage.py seed_tenant                           # create default tenant
python manage.py seed_auth_roles                       # create RBAC roles + permissions
python manage.py seed_service_catalog                  # create service categories/types
python manage.py seed_product_walkthrough --reset-demo # create realistic demo data
```

The product walkthrough creates 11 demo caregivers, organizations, and orders in a dedicated `demo-senior-platform` tenant. The `--reset-demo` flag deletes all existing demo data first (safe — never touches non-demo tenants).

## Static Asset Build

```bash
npm run css:build    # or: npx tailwindcss -i ui/css/main.css -o static/css/output.css --minify
npm run js:build     # builds Alpine.js bundle to static/ui/js/alpine.min.js
```

## Running the Server

```bash
python manage.py runserver
```

Entry URLs:
- Public marketplace: http://127.0.0.1:8000/
- UI showcase: http://127.0.0.1:8000/ui/
- Customer portal: http://127.0.0.1:8000/portal/
- Provider portal: http://127.0.0.1:8000/provider/
- Organization portal: http://127.0.0.1:8000/organization/
- Admin portal: http://127.0.0.1:8000/admin-portal/
- Django admin: http://127.0.0.1:8000/admin/
- API health: http://127.0.0.1:8000/api/v1/health/

## Running Tests

### Full Regression

```bash
python manage.py test --verbosity=2 --noinput
```

Current baseline: **2,546 tests** (262 test files, 655 test classes)

### Single App

```bash
python manage.py test apps.orders
python manage.py test apps.accounts.tests.test_profile_activation
```

### With Testing Settings (explicit)

```bash
# Linux/Mac:
DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py test

# Windows PowerShell:
$env:DJANGO_SETTINGS_MODULE="config.settings.testing"; python manage.py test
```

## Verification Commands

### System Check

```bash
python manage.py check
```

Must report 0 issues.

### Migration Drift

```bash
python manage.py makemigrations --check --dry-run
```

Known: exits 1 due to RISK-009 (pre-existing cosmetic `kernel` app metadata drift — `help_text`/`verbose_name`/`choices` only, no schema change). This is documented and accepted.

### Linting

```bash
ruff check .           # lint check
ruff format --check .  # format check
ruff format .          # auto-format
```

Configuration: `pyproject.toml` → `[tool.ruff]`

### Git Whitespace Check

```bash
git diff --check
```

Must pass clean before commit.

## Playwright Visual Tests

### Setup

```bash
cd tests/visual/
npm install
npx playwright install --with-deps chromium webkit
```

### Run

```bash
npx playwright test
```

Requires a running Django server at `http://localhost:8000` with seed data.

### Visual Baseline Regeneration

Use the GitHub Actions workflow "Generate Visual Baselines" (manual dispatch). See `08_TESTING_AND_QUALITY.md` for the full process.

## Docker Development (Alternative)

```bash
cd src/
docker-compose up --build
```

Services: PostgreSQL 16 + PostGIS, Redis 7, Django web, Celery worker, Celery beat.

All accessible at `http://localhost:8000`.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `password authentication failed for user "marketplace"` | Role not created | Run the CREATE ROLE commands above |
| `ModuleNotFoundError: No module named 'django'` | Dependencies not installed | `pip install -r requirements/base.txt` |
| `KeyError: 'MIRROR'` | Wrong settings module for tests | Set `DJANGO_SETTINGS_MODULE=config.settings.testing` explicitly |
| `makemigrations --check` exits 1 | RISK-009 cosmetic drift | Expected — no action needed |
| Tailwind classes not rendering | CSS not compiled | `npm run css:build` |
| Public site shows 0 results | Seed data in wrong tenant | Run `seed_product_walkthrough --reset-demo` |
