# DEPLOYMENT AND OPERATIONS

## Current Deployment Status

**The platform has NO production deployment infrastructure.**

This is a documented, accepted production blocker (see `04_IMPLEMENTATION_STATUS.md`). The items below describe what exists for development and what would be required for production.

---

## What Exists (Development Only)

| Component | File | Purpose |
|---|---|---|
| Docker Compose | `src/docker-compose.yml` | Local dev: PostgreSQL 16 + PostGIS, Redis 7, Django, Celery worker, Celery beat |
| Dockerfile | `src/docker/Dockerfile.dev` | Python 3.12-slim with system deps (libpq, GDAL, build tools) |
| Entrypoint | `src/docker/entrypoint.sh` | Container startup script |
| Production settings | `src/config/settings/production.py` | Django hardening (`DEBUG=False`, security middleware) — no runtime infrastructure |

## What Does NOT Exist

- Production Dockerfile (the existing one is dev-only with `runserver`)
- CD/CI deployment pipeline
- Reverse proxy configuration (nginx/Caddy)
- HTTPS/TLS configuration
- Production process manager (gunicorn/uvicorn configuration)
- Database backup strategy
- Log aggregation
- Monitoring/alerting (APM)
- Container orchestration (Kubernetes, ECS, etc.)
- Secrets management (Vault, AWS Secrets Manager, etc.)
- CDN/media storage (S3, etc.)
- Auto-scaling configuration
- Health check endpoints for load balancers (beyond `/api/v1/health/`)

---

## Production Prerequisites

### Environment Variables (Production)

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | YES | Cryptographically random, minimum 50 characters |
| `DEBUG` | YES (must be `False`) | Never `True` in production |
| `ALLOWED_HOSTS` | YES | Production domain(s) |
| `DATABASE_HOST` | YES | Production PostgreSQL host |
| `DATABASE_PORT` | YES | Default 5432 |
| `DATABASE_NAME` | YES | Production database |
| `DATABASE_USER` | YES | Production role (not superuser) |
| `DATABASE_PASSWORD` | YES | Strong password |
| `GIS_ENABLED` | Recommended `true` | Requires PostGIS + GDAL |
| `REDIS_URL` | YES | Production Redis for cache + Celery |
| `CELERY_BROKER_URL` | YES | Redis URL for task queue |

### External Services Required

| Service | Purpose | Current State |
|---|---|---|
| PostgreSQL 16 + PostGIS | Primary database | Docker dev image only |
| Redis 7 | Cache + Celery broker | Docker dev image only |
| SMS Provider (e.g., Kavenegar) | OTP delivery, notifications | **NOT INTEGRATED** |
| Payment Gateway (e.g., Zarinpal) | Payment collection | **NOT INTEGRATED** (only FakePaymentProvider) |
| Object Storage (e.g., S3) | Media files (avatars, documents, gallery) | **NOT INTEGRATED** (local FileSystemStorage) |
| Email Provider | Email notifications | **NOT INTEGRATED** |
| Push Notification Service | Mobile push | **NOT INTEGRATED** |

---

## Health Check

Existing endpoint: `GET /api/v1/health/`

Checks: database connectivity, cache connectivity. Returns JSON status.

---

## Database Management

### Migrations During Deployment

```bash
python manage.py migrate --noinput
```

Always run before starting application servers after a code update.

### Backup Strategy

Not implemented. Production deployment must include:
- Automated periodic PostgreSQL backups (pg_dump or WAL archiving)
- Tested restore procedure
- Point-in-time recovery capability

---

## Process Model

The application requires:

1. **Web server** — Django WSGI (recommended: gunicorn with multiple workers)
2. **Celery worker** — background task processing (`celery -A config worker`)
3. **Celery beat** — periodic task scheduling (`celery -A config beat`)
4. **Static file serving** — reverse proxy serves `/static/` and `/media/public/` directly
5. **Private media** — `/media/private/` must NEVER be directly served; only accessed via authenticated Django views

### Celery Beat Schedule (from settings)

| Task | Interval | Purpose |
|---|---|---|
| `publish_outbox_events` | 5 seconds | Process domain event outbox |
| `cleanup_dead_letter_events` | 24 hours | Purge old dead-letter events |
| `refresh_config_cache` | 5 minutes | Refresh configuration cache |

---

## Media Storage

### Current (Development)

Local `FileSystemStorage` under `src/media/`:
- `media/public/` — avatars, covers, gallery images (served via Django static helper in DEBUG)
- `media/private/` — verification documents (served only through authenticated admin views)

### Production Requirement

Must be replaced with object storage (S3-compatible) for:
- Durability and backup
- CDN integration for public assets
- Proper access control for private documents

Django's `STORAGES` setting (or legacy `DEFAULT_FILE_STORAGE`) is the only configuration needed — no application code depends on local-filesystem paths.

---

## Logging

Configured in `config/settings/base.py`:
- Console handler (stdout)
- Structured format: `[timestamp] LEVEL [logger] message`
- App loggers at DEBUG level
- Django/Celery loggers at INFO level
- Correlation ID middleware (`X-Correlation-ID` header) for request tracing

Production should add: file rotation, log aggregation (ELK/Loki), structured JSON output.

---

## Rollback

No automated rollback exists. Manual procedure:
1. Stop application servers
2. `git checkout <previous-tag-or-sha>`
3. `pip install -r requirements/base.txt`
4. `python manage.py migrate` (migrations must be backward-compatible or a manual revert plan prepared)
5. Restart application servers

---

## Production Blockers Summary

| Blocker | Impact | Effort |
|---|---|---|
| No real SMS delivery | Users cannot authenticate (OTP undeliverable) | Medium |
| No real payment gateway | Real money cannot flow | Medium |
| No deployment infrastructure | Cannot run in production at all | Medium |
| No object storage | Media files on ephemeral local disk | Low-medium |
| Escrow release consumer unwired | Held funds cannot reach caregiver wallets | Medium |
