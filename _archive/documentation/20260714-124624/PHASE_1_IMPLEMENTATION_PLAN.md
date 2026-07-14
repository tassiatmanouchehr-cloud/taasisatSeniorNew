# Phase 1 Implementation Plan — Platform Kernel

## Enterprise Service Marketplace Platform

**Date:** July 6, 2026
**Phase:** 1 of 7
**Status:** Ready for Implementation
**Prerequisites:** Architecture Intake Report v1.0 Approved; All blocking decisions resolved
**Estimated Duration:** 3-4 sprints
**Depends On:** Phase 0 (complete)
**Enables:** Phase 2 (Identity, Access, Configuration)

---

## Table of Contents

1. [Objectives](#1-objectives)
2. [Project Structure](#2-project-structure)
3. [Sprint Breakdown](#3-sprint-breakdown)
4. [Sprint 1 — Foundation](#4-sprint-1--foundation)
5. [Sprint 2 — Core Kernel Services](#5-sprint-2--core-kernel-services)
6. [Sprint 3 — UI Kernel & Frontend Foundation](#6-sprint-3--ui-kernel--frontend-foundation)
7. [Sprint 4 — Integration & Hardening](#7-sprint-4--integration--hardening)
8. [Technical Specifications](#8-technical-specifications)
9. [Acceptance Criteria](#9-acceptance-criteria)
10. [Risk Mitigations](#10-risk-mitigations)

---


## 1. Objectives

Phase 1 delivers the **Platform Kernel** — the non-business foundation that all 24 business modules depend on. No business workflow is implemented in this phase, but every architectural contract, shared service, and infrastructure pattern is established.

### Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| D1 | Django project scaffold | Modular monolith structure with app-per-module pattern |
| D2 | Tenant model | Multi-tenant foundation with `tenant_id` enforcement |
| D3 | User model | Custom `AbstractBaseUser` with actor/identity separation |
| D4 | RBAC foundation | Role, permission, assignment models (Module 08 groundwork) |
| D5 | Audit logging | Append-only audit envelope implementation |
| D6 | Event outbox | CES-compatible event publisher with outbox pattern |
| D7 | Configuration system | CCS-compatible config resolution with tenant override |
| D8 | Feature flag foundation | Boolean/percentage/actor-targeted flag evaluation |
| D9 | Policy versioning | Base classes for versioned business policies |
| D10 | ServiceSupplier abstraction | Supplier model, resolver, lifecycle, marketplace config |
| D11 | Shared API patterns | Base viewsets, pagination, filtering, error handling |
| D12 | Shared UI kernel | Design tokens, Tailwind config, base templates, components |
| D13 | Persian RTL layout | RTL base, Jalali integration, Persian typography |
| D14 | Docker infrastructure | Docker + Docker Compose for local development |
| D15 | Database migrations | Initial schema, indexes, constraints |
| D16 | CI foundation | GitHub Actions for lint, test, type-check |

### Non-Deliverables (explicitly out of scope)

- No business workflows (requests, matching, booking, execution, payments)
- No user registration/login flow (that's Phase 2, Module 08)
- No real identity verification or profile management
- No communication/notification sending
- No search indexing or geospatial queries
- No financial ledger entries

---


## 2. Project Structure

### Django Project Layout

```
marketplace_platform/
├── manage.py
├── pyproject.toml                    # Project metadata, dependencies
├── requirements/
│   ├── base.txt                      # Shared dependencies
│   ├── dev.txt                       # Development tools
│   ├── test.txt                      # Test dependencies
│   └── prod.txt                      # Production dependencies
├── docker/
│   ├── Dockerfile                    # Production image
│   ├── Dockerfile.dev                # Development image
│   └── entrypoint.sh
├── docker-compose.yml                # Local development stack
├── docker-compose.override.yml       # Developer-specific overrides
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Lint + test + type-check
│       └── build.yml                 # Docker image build
├── config/                           # Django project configuration
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                   # Shared settings
│   │   ├── development.py
│   │   ├── testing.py
│   │   └── production.py
│   ├── urls.py                       # Root URL configuration
│   ├── wsgi.py
│   └── asgi.py
├── apps/                             # Django applications (one per module)
│   ├── __init__.py
│   ├── kernel/                       # Module 25 — Platform Kernel
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── tenant.py
│   │   │   ├── audit.py
│   │   │   ├── event_outbox.py
│   │   │   ├── configuration.py
│   │   │   ├── feature_flag.py
│   │   │   ├── policy.py
│   │   │   └── supplier.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── tenant_service.py
│   │   │   ├── audit_service.py
│   │   │   ├── event_publisher.py
│   │   │   ├── config_resolver.py
│   │   │   ├── feature_flag_service.py
│   │   │   ├── policy_service.py
│   │   │   └── supplier_resolver.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── urls.py
│   │   │   ├── views.py
│   │   │   └── serializers.py
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── tenant_middleware.py
│   │   │   └── correlation_middleware.py
│   │   ├── management/
│   │   │   └── commands/
│   │   │       ├── seed_tenant.py
│   │   │       └── publish_outbox.py
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_tenant.py
│   │       ├── test_audit.py
│   │       ├── test_events.py
│   │       ├── test_config.py
│   │       ├── test_feature_flags.py
│   │       ├── test_policy.py
│   │       └── test_supplier.py
│   └── common/                       # Shared base classes and utilities
│       ├── __init__.py
│       ├── models.py                 # TenantAwareModel, AuditableModel, etc.
│       ├── services.py               # BaseService, BaseRepository patterns
│       ├── api/
│       │   ├── __init__.py
│       │   ├── base_viewset.py
│       │   ├── pagination.py
│       │   ├── filters.py
│       │   ├── permissions.py
│       │   ├── exceptions.py
│       │   └── error_handler.py
│       ├── enums.py
│       ├── validators.py
│       └── utils.py
├── templates/                        # Django templates (UI Kernel)
│   ├── base.html                     # Root HTML shell (RTL, Persian)
│   ├── layouts/
│   │   ├── public.html               # Public website layout
│   │   ├── portal.html               # Authenticated portal layout
│   │   ├── admin.html                # Admin panel layout
│   │   └── auth.html                 # Auth pages layout
│   ├── components/                   # Reusable UI components
│   │   ├── buttons.html
│   │   ├── forms/
│   │   ├── cards.html
│   │   ├── tables.html
│   │   ├── modals.html
│   │   ├── alerts.html
│   │   ├── navigation.html
│   │   └── ...
│   └── pages/
│       ├── errors/
│       │   ├── 400.html
│       │   ├── 403.html
│       │   ├── 404.html
│       │   └── 500.html
│       └── maintenance.html
├── static/
│   ├── css/
│   │   ├── tailwind.css              # Tailwind source
│   │   └── output.css                # Compiled CSS
│   ├── js/
│   │   ├── htmx.min.js
│   │   ├── alpine.min.js
│   │   └── app.js                    # Global JS (Jalali init, etc.)
│   ├── fonts/
│   │   └── vazirmatn/               # Persian web font
│   └── icons/
├── tailwind.config.js                # Design tokens, RTL config
├── postcss.config.js
└── locale/
    └── fa/                           # Persian translations
        └── LC_MESSAGES/
            └── django.po
```

### App Registration Pattern

Each business module (Phase 2+) will follow the same pattern:
```
apps/{module_name}/
├── models/
├── services/
├── api/
├── events/          # CES event definitions for this module
├── policies/        # Versioned policy implementations
├── permissions/     # Protected operations catalog
├── migrations/
├── admin.py
├── apps.py
└── tests/
```

---


## 3. Sprint Breakdown

| Sprint | Focus | Key Deliverables |
|--------|-------|-----------------|
| Sprint 1 | Foundation | Docker, Django scaffold, tenant model, user model, database, base classes |
| Sprint 2 | Core Kernel Services | Event outbox, audit logging, configuration, feature flags, policy versioning, ServiceSupplier |
| Sprint 3 | UI Kernel & Frontend | Tailwind config, design tokens, base templates, RTL layout, Jalali, components |
| Sprint 4 | Integration & Hardening | API patterns, CI pipeline, test suite, documentation, end-to-end verification |

---

## 4. Sprint 1 — Foundation

### 4.1 Docker & Infrastructure Setup

**Files to create:**
- `docker/Dockerfile.dev` — Python 3.12 + system dependencies
- `docker-compose.yml` — PostgreSQL 16, Redis 7, Django dev server
- `docker-compose.override.yml` — Volume mounts, port mappings for dev

**Docker Compose services:**
```yaml
services:
  db:         PostgreSQL 16 + PostGIS 3.4
  redis:      Redis 7 Alpine
  web:        Django development server
  celery:     Celery worker
  beat:       Celery beat scheduler
  tailwind:   Tailwind CSS watcher (build mode)
```

**Environment variables (`.env.example`):**
```
DJANGO_SETTINGS_MODULE=config.settings.development
DATABASE_URL=postgres://marketplace:marketplace@db:5432/marketplace
REDIS_URL=redis://redis:6379/0
SECRET_KEY=dev-only-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 4.2 Django Project Scaffold

**`pyproject.toml` key dependencies:**
```toml
[project]
name = "marketplace-platform"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "django>=5.1,<5.3",
    "djangorestframework>=3.15",
    "djangorestframework-simplejwt>=5.3",
    "django-filter>=24.0",
    "drf-spectacular>=0.27",
    "psycopg[binary]>=3.1",
    "django-redis>=5.4",
    "celery[redis]>=5.4",
    "django-celery-beat>=2.6",
    "jdatetime>=5.0",
    "django-cors-headers>=4.3",
    "python-decouple>=3.8",
    "gunicorn>=22.0",
]
```

**Settings structure (`config/settings/base.py`):**
- `INSTALLED_APPS`: kernel, common, rest_framework, drf_spectacular, django_filters, corsheaders, django_celery_beat
- `AUTH_USER_MODEL`: `kernel.User`
- `DEFAULT_AUTO_FIELD`: `django.db.models.UUIDField` (custom primary key mixin instead)
- REST framework defaults: JWT auth, pagination, exception handler, schema class
- Database: PostgreSQL with `django.contrib.gis` ready (PostGIS)
- Cache: Redis
- Celery: Redis broker + result backend
- Internationalization: `fa-ir` as default, `USE_TZ = True`

### 4.3 Tenant Model

```python
# apps/kernel/models/tenant.py

class Tenant(models.Model):
    """
    Root entity for multi-tenant isolation.
    Every business record belongs to exactly one tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    domain = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=TenantStatus.choices, default=TenantStatus.ACTIVE)
    settings = models.JSONField(default=dict, blank=True)  # Tenant-level overrides
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = 'kernel_tenant'
```

**TenantAwareModel base class:**
```python
# apps/common/models.py

class TenantAwareModel(models.Model):
    """Base model for all tenant-owned entities."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('kernel.Tenant', on_delete=models.PROTECT, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            raise ValueError("tenant_id is required for all tenant-aware models")
        super().save(*args, **kwargs)
```

**Tenant middleware:**
```python
# apps/kernel/middleware/tenant_middleware.py

class TenantMiddleware:
    """
    Resolves tenant from request context.
    Resolution order: header → JWT claim → domain → deny.
    """
    def __call__(self, request):
        request.tenant = self.resolve_tenant(request)
        response = self.get_response(request)
        return response
```

### 4.4 User Model

```python
# apps/kernel/models/user.py

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model. Minimal auth entity.
    Profile/identity details owned by Module 08 (Phase 2).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('kernel.Tenant', on_delete=models.PROTECT)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    # Actor reference — links to the canonical actor concept
    actor_type = models.CharField(max_length=50, blank=True)  # placeholder for Module 08

    USERNAME_FIELD = 'id'  # UUID-based; login via phone/email resolved in Module 08

    objects = UserManager()

    class Meta:
        db_table = 'kernel_user'
```

### 4.5 RBAC Foundation (Module 08 Groundwork)

```python
# apps/kernel/models/rbac.py

class Role(TenantAwareModel):
    """Role definition. Module 08 will own full role lifecycle."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)  # Built-in vs custom
    permissions = models.JSONField(default=list)  # Permission keys
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'kernel_role'
        unique_together = ['tenant', 'slug']


class RoleAssignment(TenantAwareModel):
    """Binds a user to a role within a scope."""
    user = models.ForeignKey('kernel.User', on_delete=models.CASCADE, related_name='role_assignments')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    scope_type = models.CharField(max_length=50, blank=True)  # 'organization', 'platform', etc.
    scope_id = models.UUIDField(null=True, blank=True)  # ID of scoped entity
    is_active = models.BooleanField(default=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'kernel_role_assignment'


class Permission(models.Model):
    """
    Permission registry. Each module registers its protected operations.
    Module 08 evaluates these; other modules only define them.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=200, unique=True)  # e.g., 'request.draft.create'
    module_id = models.CharField(max_length=10)  # e.g., 'M01'
    resource_type = models.CharField(max_length=100)
    action = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    default_roles = models.JSONField(default=list)  # Roles allowed by default
    requires_scope = models.BooleanField(default=False)
    audit_required = models.BooleanField(default=True)

    class Meta:
        db_table = 'kernel_permission'
```

---


## 5. Sprint 2 — Core Kernel Services

### 5.1 Event Outbox (CES Publisher)

```python
# apps/kernel/models/event_outbox.py

class EventOutbox(models.Model):
    """
    Transactional outbox for CES events.
    Events are written in the same DB transaction as business state,
    then published asynchronously by a background worker.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField()
    event_type = models.CharField(max_length=200)  # e.g., 'Request.Created.v1'
    event_version = models.CharField(max_length=10, default='1.0')
    payload = models.JSONField()
    occurred_at = models.DateTimeField()
    published_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending',
                              choices=[('pending','Pending'),('published','Published'),
                                       ('failed','Failed'),('dead_letter','Dead Letter')])
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=5)
    correlation_id = models.UUIDField()
    causation_id = models.UUIDField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)
    source_module = models.CharField(max_length=10)
    actor_id = models.UUIDField(null=True, blank=True)
    privacy_class = models.CharField(max_length=20, default='internal')
    audit_class = models.CharField(max_length=20, default='standard')
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'kernel_event_outbox'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['tenant_id', 'event_type']),
            models.Index(fields=['correlation_id']),
        ]
```

**Event Publisher Service:**
```python
# apps/kernel/services/event_publisher.py

class EventPublisher:
    """
    Publishes CES-envelope-compatible events to the outbox.
    All business modules use this service to emit events.
    """
    @staticmethod
    def publish(
        tenant_id: UUID,
        event_type: str,
        payload: dict,
        source_module: str,
        actor_id: UUID | None = None,
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
        idempotency_key: str = '',
        privacy_class: str = 'internal',
        audit_class: str = 'standard',
    ) -> EventOutbox:
        """Create an event in the outbox within the current transaction."""
        return EventOutbox.objects.create(
            tenant_id=tenant_id,
            event_type=event_type,
            event_version='1.0',
            payload=payload,
            occurred_at=timezone.now(),
            source_module=source_module,
            actor_id=actor_id,
            correlation_id=correlation_id or uuid.uuid4(),
            causation_id=causation_id,
            idempotency_key=idempotency_key,
            privacy_class=privacy_class,
            audit_class=audit_class,
        )
```

**Outbox Publisher Worker (Celery task):**
```python
# apps/kernel/tasks.py

@shared_task(name='kernel.publish_outbox_events')
def publish_outbox_events(batch_size=100):
    """
    Polls pending events from outbox and publishes to Redis/Celery consumers.
    Runs every 1-5 seconds via Celery Beat.
    """
    pending = EventOutbox.objects.filter(
        status='pending'
    ).order_by('created_at')[:batch_size]

    for event in pending:
        try:
            dispatch_event.delay(str(event.id))
            event.status = 'published'
            event.published_at = timezone.now()
        except Exception as e:
            event.retry_count += 1
            event.error_message = str(e)
            if event.retry_count >= event.max_retries:
                event.status = 'dead_letter'
            else:
                event.status = 'failed'
        event.save()
```

### 5.2 Audit Logging

```python
# apps/kernel/models/audit.py

class AuditLog(models.Model):
    """
    Append-only audit record following Module 25 Audit Envelope Standard.
    Never updated or deleted.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField()
    occurred_at = models.DateTimeField(default=timezone.now)
    actor_id = models.UUIDField(null=True)
    actor_type = models.CharField(max_length=50, blank=True)
    actor_display = models.CharField(max_length=255, blank=True)
    impersonator_id = models.UUIDField(null=True, blank=True)
    action = models.CharField(max_length=200)  # e.g., 'policy.publish'
    resource_type = models.CharField(max_length=100)
    resource_id = models.UUIDField(null=True, blank=True)
    module_id = models.CharField(max_length=10)
    before_snapshot = models.JSONField(null=True, blank=True)  # Hashed/redacted
    after_snapshot = models.JSONField(null=True, blank=True)
    reason = models.TextField(blank=True)
    correlation_id = models.UUIDField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    audit_class = models.CharField(max_length=20, default='standard',
                                   choices=[('standard','Standard'),('financial','Financial'),
                                            ('security','Security'),('compliance','Compliance')])
    retention_policy = models.CharField(max_length=50, default='standard')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'kernel_audit_log'
        indexes = [
            models.Index(fields=['tenant_id', 'occurred_at']),
            models.Index(fields=['actor_id', 'occurred_at']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['correlation_id']),
            models.Index(fields=['action']),
        ]
        # Partitioning by occurred_at (configured at DB level)
```

**Audit Service:**
```python
# apps/kernel/services/audit_service.py

class AuditService:
    @staticmethod
    def log(
        tenant_id: UUID,
        action: str,
        resource_type: str,
        module_id: str,
        actor_id: UUID | None = None,
        resource_id: UUID | None = None,
        before: dict | None = None,
        after: dict | None = None,
        reason: str = '',
        audit_class: str = 'standard',
        request=None,
    ) -> AuditLog:
        """Create an immutable audit record."""
        return AuditLog.objects.create(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            module_id=module_id,
            before_snapshot=before,
            after_snapshot=after,
            reason=reason,
            audit_class=audit_class,
            correlation_id=getattr(request, 'correlation_id', None) if request else None,
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else '',
        )
```

### 5.3 Configuration System (CCS)

```python
# apps/kernel/models/configuration.py

class ConfigurationKey(models.Model):
    """
    Registry of all CCS configuration keys.
    Each key has exactly one owning module.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=200, unique=True)  # e.g., 'marketplace.supplier_model'
    owner_module = models.CharField(max_length=10)
    schema_version = models.CharField(max_length=10, default='1.0')
    scope_level = models.CharField(max_length=30)  # platform|tenant|organization|...
    value_type = models.CharField(max_length=20)  # boolean|string|number|object|array|enum
    default_value = models.JSONField(null=True, blank=True)
    validation_schema = models.JSONField(null=True, blank=True)  # JSON Schema for value
    override_policy = models.CharField(max_length=30, default='tenant_override')
    change_requires_approval = models.BooleanField(default=False)
    activation_mode = models.CharField(max_length=20, default='immediate')
    description = models.TextField(blank=True)
    is_sensitive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'kernel_configuration_key'


class ConfigurationValue(TenantAwareModel):
    """
    Tenant-specific override for a configuration key.
    If no override exists, the key's default_value is used.
    """
    config_key = models.ForeignKey(ConfigurationKey, on_delete=models.CASCADE,
                                    related_name='overrides')
    scope_type = models.CharField(max_length=30, blank=True)  # 'tenant', 'organization', etc.
    scope_id = models.UUIDField(null=True, blank=True)
    value = models.JSONField()
    is_active = models.BooleanField(default=True)
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_until = models.DateTimeField(null=True, blank=True)
    approved_by = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'kernel_configuration_value'
        indexes = [
            models.Index(fields=['tenant_id', 'config_key_id', 'is_active']),
        ]
```

**Config Resolver Service:**
```python
# apps/kernel/services/config_resolver.py

class ConfigResolver:
    """
    Resolves configuration values using CCS scope resolution:
    1. Actor-specific override
    2. Organization-specific override
    3. Tenant-specific override
    4. Platform default
    """
    @classmethod
    def get(cls, key: str, tenant_id: UUID, scope_context: dict | None = None) -> Any:
        """Resolve a configuration value for the given context."""
        # Check cache first (Redis)
        cache_key = f"config:{tenant_id}:{key}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Resolve from DB with scope hierarchy
        config_key = ConfigurationKey.objects.get(key=key)
        value = cls._resolve_with_scope(config_key, tenant_id, scope_context)

        # Cache with TTL
        cache.set(cache_key, value, timeout=300)
        return value
```

### 5.4 Feature Flag Foundation

```python
# apps/kernel/models/feature_flag.py

class FeatureFlag(TenantAwareModel):
    """Feature flag with targeting rules."""
    key = models.CharField(max_length=200)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    flag_type = models.CharField(max_length=20, default='boolean',
                                  choices=[('boolean','Boolean'),('percentage','Percentage'),
                                           ('actor_list','Actor List'),('rule_based','Rule Based')])
    is_enabled = models.BooleanField(default=False)
    percentage = models.IntegerField(default=0)  # For gradual rollout
    targeting_rules = models.JSONField(default=dict, blank=True)
    kill_switch = models.BooleanField(default=False)  # Emergency disable
    owner_module = models.CharField(max_length=10, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'kernel_feature_flag'
        unique_together = ['tenant', 'key']
```

### 5.5 Policy Versioning Foundation

```python
# apps/kernel/models/policy.py

class PolicyDefinition(TenantAwareModel):
    """
    A versioned business policy container.
    Specific rule payloads are module-defined; this is the governance envelope.
    """
    policy_type = models.CharField(max_length=100)  # e.g., 'commission', 'matching_ranking'
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner_module = models.CharField(max_length=10)
    current_version = models.IntegerField(default=1)
    status = models.CharField(max_length=20, default='draft',
                              choices=[('draft','Draft'),('active','Active'),
                                       ('deprecated','Deprecated'),('archived','Archived')])
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'kernel_policy_definition'
        unique_together = ['tenant', 'policy_type', 'name']


class PolicyVersion(TenantAwareModel):
    """
    Immutable snapshot of a policy at a point in time.
    Never overwrite — always create new versions.
    """
    policy = models.ForeignKey(PolicyDefinition, on_delete=models.CASCADE,
                               related_name='versions')
    version_number = models.IntegerField()
    rule_payload = models.JSONField()  # Module-specific rule structure
    validation_schema = models.JSONField(null=True, blank=True)
    effective_from = models.DateTimeField()
    effective_until = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='draft')
    approved_by = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    change_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'kernel_policy_version'
        unique_together = ['policy', 'version_number']
        ordering = ['-version_number']
```

### 5.6 ServiceSupplier Abstraction

```python
# apps/kernel/models/supplier.py

class SupplierType(models.TextChoices):
    INDEPENDENT_PROVIDER = 'INDEPENDENT_PROVIDER', 'Independent Provider'
    ORGANIZATION = 'ORGANIZATION', 'Organization'
    ORGANIZATION_PROVIDER = 'ORGANIZATION_PROVIDER', 'Organization Provider'


class SupplierStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ACTIVE = 'active', 'Active'
    SUSPENDED = 'suspended', 'Suspended'
    DEACTIVATED = 'deactivated', 'Deactivated'


class AvailabilityStatus(models.TextChoices):
    AVAILABLE = 'available', 'Available'
    BUSY = 'busy', 'Busy'
    OFFLINE = 'offline', 'Offline'
    ON_LEAVE = 'on_leave', 'On Leave'


class VerificationLevel(models.TextChoices):
    UNVERIFIED = 'unverified', 'Unverified'
    BASIC = 'basic', 'Basic'
    ADVANCED = 'advanced', 'Advanced'
    PREMIUM = 'premium', 'Premium'


class ServiceSupplier(TenantAwareModel):
    """
    Universal abstraction for any entity that can receive, accept, fulfill,
    or be financially credited for a service order.
    """
    supplier_type = models.CharField(max_length=30, choices=SupplierType.choices)
    linked_entity_id = models.UUIDField()
    linked_entity_type = models.CharField(max_length=100)
    display_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=SupplierStatus.choices,
                              default=SupplierStatus.PENDING)
    capabilities = models.JSONField(default=dict, blank=True)
    service_categories = models.JSONField(default=list, blank=True)
    availability_status = models.CharField(max_length=20, choices=AvailabilityStatus.choices,
                                           default=AvailabilityStatus.OFFLINE)
    verification_level = models.CharField(max_length=20, choices=VerificationLevel.choices,
                                          default=VerificationLevel.UNVERIFIED)
    financial_party_id = models.UUIDField(null=True, blank=True)
    reputation_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    module_id = models.CharField(max_length=10, default='M25')
    entity_type = models.CharField(max_length=100, default='ServiceSupplier')
    external_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'kernel_service_supplier'
        indexes = [
            models.Index(fields=['tenant_id', 'supplier_type']),
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['linked_entity_id', 'linked_entity_type']),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.get_supplier_type_display()})"
```

**Supplier Resolver Service:**
```python
# apps/kernel/services/supplier_resolver.py

class SupplierResolver:
    """
    Resolves supplier entities based on tenant marketplace model configuration.
    Business modules call this instead of directly querying organizations/providers.
    """
    @classmethod
    def resolve(cls, candidate_id: UUID, tenant_id: UUID) -> ServiceSupplier:
        """Resolve a candidate reference to a ServiceSupplier entity."""
        return ServiceSupplier.objects.get(id=candidate_id, tenant_id=tenant_id)

    @classmethod
    def get_active_suppliers(cls, tenant_id: UUID, supplier_type: str | None = None):
        """Get active suppliers filtered by marketplace model config."""
        marketplace_model = ConfigResolver.get('marketplace.supplier_model', tenant_id)
        qs = ServiceSupplier.objects.filter(tenant_id=tenant_id, status=SupplierStatus.ACTIVE)

        if supplier_type:
            qs = qs.filter(supplier_type=supplier_type)
        elif marketplace_model == 'independent_only':
            qs = qs.filter(supplier_type=SupplierType.INDEPENDENT_PROVIDER)
        elif marketplace_model == 'organization_only':
            qs = qs.filter(supplier_type=SupplierType.ORGANIZATION)
        # 'hybrid' returns all types

        return qs

    @classmethod
    def is_supplier_type_allowed(cls, tenant_id: UUID, supplier_type: str) -> bool:
        """Check if a supplier type is allowed by tenant configuration."""
        marketplace_model = ConfigResolver.get('marketplace.supplier_model', tenant_id)
        if marketplace_model == 'independent_only':
            return supplier_type == SupplierType.INDEPENDENT_PROVIDER
        elif marketplace_model == 'organization_only':
            return supplier_type in (SupplierType.ORGANIZATION, SupplierType.ORGANIZATION_PROVIDER)
        return True  # hybrid allows all
```

---


## 6. Sprint 3 — UI Kernel & Frontend Foundation

### 6.1 Tailwind Configuration (Design Tokens)

```javascript
// tailwind.config.js
const plugin = require('tailwindcss/plugin')

module.exports = {
  content: ['./templates/**/*.html', './static/js/**/*.js'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff', 100: '#dbeafe', 200: '#bfdbfe',
          300: '#93c5fd', 400: '#60a5fa', 500: '#3b82f6',
          600: '#2563eb', 700: '#1d4ed8', 800: '#1e40af', 900: '#1e3a8a',
        },
        secondary: { /* ... */ },
        accent: { /* ... */ },
        success: { 500: '#22c55e' },
        warning: { 500: '#f59e0b' },
        danger: { 500: '#ef4444' },
        info: { 500: '#06b6d4' },
        surface: { DEFAULT: '#ffffff', dark: '#1f2937' },
      },
      fontFamily: {
        sans: ['Vazirmatn', 'IRANSans', 'Tahoma', 'Arial', 'sans-serif'],
        mono: ['JetBrains Mono', 'Courier New', 'monospace'],
      },
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1.5' }],
        sm: ['0.875rem', { lineHeight: '1.5' }],
        base: ['1rem', { lineHeight: '1.75' }],
        lg: ['1.125rem', { lineHeight: '1.75' }],
        xl: ['1.25rem', { lineHeight: '1.75' }],
        '2xl': ['1.5rem', { lineHeight: '1.5' }],
        '3xl': ['1.875rem', { lineHeight: '1.4' }],
        '4xl': ['2.25rem', { lineHeight: '1.3' }],
      },
      spacing: {
        '0.5': '0.125rem', '1.5': '0.375rem', '2.5': '0.625rem',
        '3.5': '0.875rem', '4.5': '1.125rem',
      },
      borderRadius: {
        sm: '0.25rem', DEFAULT: '0.5rem', md: '0.625rem',
        lg: '0.75rem', xl: '1rem', '2xl': '1.5rem',
      },
      zIndex: {
        dropdown: '1000', sticky: '1020', fixed: '1030',
        modal: '1050', toast: '1060', tooltip: '1070',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    // RTL support via logical properties
    plugin(function({ addBase }) {
      addBase({ 'html': { direction: 'rtl' } })
    }),
  ],
}
```

### 6.2 Base HTML Template

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="fa-IR" dir="rtl" class="{% block html_class %}{% endblock %}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}{% endblock %} | {% block site_name %}پلتفرم{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'css/output.css' %}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@100..900&display=swap" rel="stylesheet">
    {% block extra_head %}{% endblock %}
</head>
<body class="font-sans bg-gray-50 text-gray-900 antialiased min-h-screen"
      x-data="{ sidebarOpen: false }"
      hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
    {% block body %}{% endblock %}
    <script src="{% static 'js/htmx.min.js' %}"></script>
    <script src="{% static 'js/alpine.min.js' %}" defer></script>
    <script src="{% static 'js/app.js' %}"></script>
    {% block extra_scripts %}{% endblock %}
</body>
</html>
```

### 6.3 Layout Templates

**Portal Layout (authenticated users):**
```html
<!-- templates/layouts/portal.html -->
{% extends "base.html" %}
{% block body %}
<div class="flex min-h-screen">
    <!-- Sidebar (RTL: opens from right) -->
    <aside class="w-64 bg-white border-l border-gray-200 shadow-sm hidden lg:block"
           :class="{ 'block': sidebarOpen, 'hidden': !sidebarOpen }">
        {% include "components/navigation/sidebar.html" %}
    </aside>

    <!-- Main content -->
    <div class="flex-1 flex flex-col">
        <!-- Top navbar -->
        <header class="h-16 bg-white border-b border-gray-200 flex items-center px-6">
            {% include "components/navigation/topbar.html" %}
        </header>

        <!-- Page content -->
        <main class="flex-1 p-6">
            {% block content %}{% endblock %}
        </main>
    </div>
</div>
{% endblock %}
```

### 6.4 Reusable Components (Template Includes)

**Button component:**
```html
<!-- templates/components/button.html -->
{% comment %}
Usage: {% include "components/button.html" with text="ذخیره" variant="primary" size="md" %}
Variants: primary, secondary, danger, ghost
Sizes: sm, md, lg
{% endcomment %}
<button type="{{ type|default:'button' }}"
        class="inline-flex items-center justify-center font-medium rounded-lg
               transition-colors duration-200 focus:outline-none focus:ring-2
               focus:ring-offset-2
               {% if variant == 'primary' %}
                 bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500
               {% elif variant == 'danger' %}
                 bg-danger-500 text-white hover:bg-red-700 focus:ring-red-500
               {% elif variant == 'ghost' %}
                 bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-gray-500
               {% else %}
                 bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 focus:ring-primary-500
               {% endif %}
               {% if size == 'sm' %}px-3 py-1.5 text-sm
               {% elif size == 'lg' %}px-6 py-3 text-lg
               {% else %}px-4 py-2 text-base{% endif %}"
        {% if disabled %}disabled{% endif %}
        {{ attrs|default:'' }}>
    {% if icon_start %}{{ icon_start }}{% endif %}
    {{ text }}
    {% if icon_end %}{{ icon_end }}{% endif %}
</button>
```

**Alert component:**
```html
<!-- templates/components/alert.html -->
{% comment %}
Usage: {% include "components/alert.html" with type="success" message="عملیات موفق بود" %}
Types: success, warning, danger, info
{% endcomment %}
<div class="rounded-lg p-4 flex items-start gap-3
            {% if type == 'success' %}bg-green-50 text-green-800 border border-green-200
            {% elif type == 'warning' %}bg-yellow-50 text-yellow-800 border border-yellow-200
            {% elif type == 'danger' %}bg-red-50 text-red-800 border border-red-200
            {% else %}bg-blue-50 text-blue-800 border border-blue-200{% endif %}"
     role="alert">
    <span class="text-lg">
        {% if type == 'success' %}✓{% elif type == 'warning' %}⚠{% elif type == 'danger' %}✕{% else %}ℹ{% endif %}
    </span>
    <div>
        {% if title %}<p class="font-semibold">{{ title }}</p>{% endif %}
        <p>{{ message }}</p>
    </div>
</div>
```

### 6.5 Jalali Date Integration

```javascript
// static/js/app.js

// Jalali date formatting utility
const JalaliUtils = {
    // Convert Gregorian ISO string to Jalali display
    toJalali(isoString) {
        if (!isoString) return '';
        // Using dayjs with jalali plugin (loaded separately)
        return dayjs(isoString).calendar('jalali').locale('fa').format('YYYY/MM/DD');
    },

    toJalaliDateTime(isoString) {
        if (!isoString) return '';
        return dayjs(isoString).calendar('jalali').locale('fa').format('YYYY/MM/DD HH:mm');
    },

    // Persian digit conversion
    toPersianDigits(str) {
        const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
        return String(str).replace(/[0-9]/g, d => persianDigits[d]);
    },
};

// Auto-convert elements with data-jalali attribute
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-jalali]').forEach(el => {
        const iso = el.getAttribute('data-jalali');
        el.textContent = JalaliUtils.toJalali(iso);
    });

    document.querySelectorAll('[data-jalali-datetime]').forEach(el => {
        const iso = el.getAttribute('data-jalali-datetime');
        el.textContent = JalaliUtils.toJalaliDateTime(iso);
    });
});
```

### 6.6 Persian RTL Foundation

Key RTL rules enforced by the design system:
- All Tailwind utilities use logical properties where available
- Sidebar renders on the right (RTL natural)
- Tables scroll left-to-right naturally
- Form labels align to the right
- Breadcrumbs flow right-to-left
- Icon mirroring for directional icons (arrows, chevrons)
- Mixed BiDi text handled by browser + `unicode-bidi: plaintext` where needed

---


## 7. Sprint 4 — Integration & Hardening

### 7.1 Shared API Patterns

**Base ViewSet:**
```python
# apps/common/api/base_viewset.py

class TenantAwareViewSet(viewsets.ModelViewSet):
    """
    Base viewset that enforces tenant isolation on all queries.
    All business module viewsets must extend this.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return qs.filter(tenant=self.request.tenant)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.tenant,
            created_by=self.request.user.id if self.request.user.is_authenticated else None,
        )
```

**Standard Pagination:**
```python
# apps/common/api/pagination.py

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'page': self.page.number,
            'page_size': self.page.paginator.per_page,
            'total_pages': self.page.paginator.num_pages,
            'results': data,
        })
```

**Shared Error Handler:**
```python
# apps/common/api/error_handler.py

def custom_exception_handler(exc, context):
    """
    Maps exceptions to the Module 25 Shared Error Model format.
    Never exposes internal exception names.
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_body = {
            'error_code': map_to_error_code(exc),
            'message': get_safe_message(exc),
            'category': get_error_category(exc),
            'severity': get_error_severity(exc),
            'retryable': is_retryable(exc),
            'correlation_id': str(getattr(context['request'], 'correlation_id', '')),
            'tenant_id': str(getattr(context['request'], 'tenant_id', '')),
            'details': get_safe_details(exc),
        }
        response.data = error_body

    return response
```

**Correlation Middleware:**
```python
# apps/kernel/middleware/correlation_middleware.py

class CorrelationMiddleware:
    """
    Ensures every request has a correlation_id for tracing.
    Passes through existing correlation_id from headers or generates new.
    """
    def __call__(self, request):
        correlation_id = request.headers.get('X-Correlation-ID')
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        request.correlation_id = correlation_id
        response = self.get_response(request)
        response['X-Correlation-ID'] = correlation_id
        return response
```

### 7.2 Management Commands

```python
# Seed initial tenant for development
# apps/kernel/management/commands/seed_tenant.py
class Command(BaseCommand):
    """Create a default development tenant with marketplace config."""
    def handle(self, *args, **options):
        tenant, created = Tenant.objects.get_or_create(
            slug='dev',
            defaults={
                'name': 'Development Tenant',
                'status': TenantStatus.ACTIVE,
                'settings': {'marketplace_model': 'hybrid'},
            }
        )
        # Seed marketplace configuration keys
        self._seed_marketplace_config(tenant)
        # Seed default roles
        self._seed_default_roles(tenant)
```

### 7.3 Initial Configuration Seeds

Marketplace configuration keys seeded on first migration:

```python
MARKETPLACE_CONFIG_SEEDS = [
    {
        'key': 'marketplace.supplier_model',
        'owner_module': 'M19',
        'scope_level': 'tenant',
        'value_type': 'enum',
        'default_value': 'hybrid',
        'description': 'Marketplace supplier model: independent_only, organization_only, hybrid',
    },
    {
        'key': 'marketplace.allow_independent_providers',
        'owner_module': 'M19',
        'scope_level': 'tenant',
        'value_type': 'boolean',
        'default_value': True,
    },
    {
        'key': 'marketplace.allow_organizations',
        'owner_module': 'M19',
        'scope_level': 'tenant',
        'value_type': 'boolean',
        'default_value': True,
    },
    {
        'key': 'marketplace.allow_direct_organization_provider_matching',
        'owner_module': 'M19',
        'scope_level': 'tenant',
        'value_type': 'boolean',
        'default_value': False,
    },
    {
        'key': 'marketplace.organization_requires_internal_assignment',
        'owner_module': 'M19',
        'scope_level': 'tenant',
        'value_type': 'boolean',
        'default_value': False,
    },
    {
        'key': 'marketplace.independent_provider_self_acceptance_enabled',
        'owner_module': 'M19',
        'scope_level': 'tenant',
        'value_type': 'boolean',
        'default_value': True,
    },
    {
        'key': 'marketplace.organization_auto_accepts_orders',
        'owner_module': 'M19',
        'scope_level': 'tenant',
        'value_type': 'boolean',
        'default_value': False,
    },
    {
        'key': 'marketplace.organization_provider_direct_payout_enabled',
        'owner_module': 'M19',
        'scope_level': 'tenant',
        'value_type': 'boolean',
        'default_value': False,
    },
    {
        'key': 'marketplace.customer_can_choose_supplier_type',
        'owner_module': 'M19',
        'scope_level': 'tenant',
        'value_type': 'boolean',
        'default_value': True,
    },
    {
        'key': 'marketplace.search_show_supplier_type_filter',
        'owner_module': 'M19',
        'scope_level': 'tenant',
        'value_type': 'boolean',
        'default_value': True,
    },
]
```

### 7.4 CI Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgis/postgis:16-3.4
        env:
          POSTGRES_DB: test_marketplace
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ['5432:5432']
      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements/test.txt
      - run: python manage.py test --settings=config.settings.testing
      - run: ruff check .
      - run: ruff format --check .
```

### 7.5 Test Strategy

**Required test categories for Phase 1:**

| Category | What is tested | Minimum coverage |
|----------|---------------|-----------------|
| Tenant isolation | Every query is tenant-scoped; cross-tenant access denied | Every model |
| Event outbox | Events written in transaction; published correctly; dead-letter on failure | All publisher paths |
| Audit logging | Audit records created; immutable; correct envelope fields | All audit-worthy operations |
| Config resolution | Scope hierarchy resolves correctly; caching works; tenant overrides win | All resolution paths |
| Feature flags | Boolean/percentage/actor evaluation correct | All flag types |
| Policy versioning | Create/activate/deprecate; version ordering; effective date resolution | All lifecycle states |
| Supplier abstraction | CRUD; marketplace model filtering; type validation; resolver logic | All supplier types |
| Supplier models | independent_only, organization_only, hybrid — all work by config only | Three config variants |
| API error handling | Errors match Shared Error Model format; no internal leaks | All error categories |
| Middleware | Tenant resolved correctly; correlation_id propagated | All middleware |

---


## 8. Technical Specifications

### 8.1 Database Schema Summary (Phase 1 Tables)

| Table | Purpose | Module |
|-------|---------|--------|
| `kernel_tenant` | Multi-tenant root entity | M25 |
| `kernel_user` | Authentication user (custom AbstractBaseUser) | M25 |
| `kernel_role` | Role definitions | M25 (M08 groundwork) |
| `kernel_role_assignment` | User-to-role bindings with scope | M25 (M08 groundwork) |
| `kernel_permission` | Protected operations registry | M25 |
| `kernel_audit_log` | Append-only audit records | M25 |
| `kernel_event_outbox` | CES event outbox (transactional) | M25 |
| `kernel_configuration_key` | CCS config key registry | M25 |
| `kernel_configuration_value` | Tenant-specific config overrides | M25 |
| `kernel_feature_flag` | Feature flag definitions with targeting | M25 |
| `kernel_policy_definition` | Versioned policy containers | M25 |
| `kernel_policy_version` | Immutable policy version snapshots | M25 |
| `kernel_service_supplier` | ServiceSupplier abstraction | M25 |

**Total Phase 1 tables: 13**

### 8.2 API Endpoints (Phase 1 — Internal/Admin Only)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/health/` | Health check |
| GET | `/api/v1/config/{key}/` | Resolve config value for current tenant |
| GET | `/api/v1/flags/{key}/` | Evaluate feature flag |
| GET | `/api/v1/suppliers/` | List suppliers (filtered by marketplace model) |
| GET | `/api/v1/suppliers/{id}/` | Get supplier detail |
| GET | `/api/v1/audit/` | List audit records (admin only) |
| GET | `/api/v1/events/` | List outbox events (admin only) |

> Full CRUD APIs for configuration, flags, policies, and suppliers will be implemented
> but gated behind platform-owner permissions. Business-facing APIs come in Phase 2+.

### 8.3 Middleware Stack (Order Matters)

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'apps.kernel.middleware.correlation_middleware.CorrelationMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.kernel.middleware.tenant_middleware.TenantMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### 8.4 Celery Tasks (Phase 1)

| Task | Schedule | Purpose |
|------|----------|---------|
| `kernel.publish_outbox_events` | Every 2 seconds | Publish pending events from outbox |
| `kernel.cleanup_dead_letter_events` | Daily | Archive/report dead-letter events |
| `kernel.refresh_config_cache` | Every 5 minutes | Invalidate stale config cache entries |

### 8.5 Redis Key Structure

```
config:{tenant_id}:{key}          — Cached configuration values (TTL: 300s)
flag:{tenant_id}:{key}            — Cached feature flag evaluations (TTL: 60s)
rate_limit:{tenant_id}:{actor}:{action} — Rate limiting counters
lock:{resource_type}:{resource_id} — Distributed locks (Redlock pattern)
```

---

## 9. Acceptance Criteria

Phase 1 is complete when ALL of the following pass:

### Infrastructure
- [ ] `docker-compose up` starts all services (db, redis, web, celery, beat) in <60s
- [ ] `python manage.py migrate` runs cleanly on fresh database
- [ ] `python manage.py test` passes with 0 failures
- [ ] `ruff check .` and `ruff format --check .` pass (linting)
- [ ] GitHub Actions CI pipeline passes on push

### Tenant Isolation
- [ ] Creating a record without `tenant_id` raises an error
- [ ] Querying records returns only records from the current tenant
- [ ] Cross-tenant access is explicitly denied (returns 403/404, not data from other tenant)
- [ ] Admin can see all tenants (platform-scoped permission)

### Event Outbox
- [ ] Business operation + event write happen in one DB transaction
- [ ] Outbox publisher delivers pending events to consumers
- [ ] Failed events retry with backoff, eventually reach dead-letter
- [ ] Event payload matches CES Kernel Envelope structure

### Audit Logging
- [ ] Audit records are append-only (no UPDATE/DELETE on audit table)
- [ ] Audit record contains all required envelope fields
- [ ] Sensitive data is redacted/hashed in audit records
- [ ] Correlation ID links audit to originating request

### Configuration
- [ ] Config values resolve in correct scope order (actor → org → tenant → platform)
- [ ] Tenant overrides take precedence over defaults
- [ ] Config changes are audited
- [ ] Config values are cached in Redis with appropriate TTL

### Feature Flags
- [ ] Boolean flag evaluates correctly (on/off per tenant)
- [ ] Percentage-based flag produces expected distribution
- [ ] Kill switch immediately disables a feature
- [ ] Flag evaluation is cached

### Policy Versioning
- [ ] Policies can be created, versioned, activated, deprecated
- [ ] Only one version is active at a time per policy
- [ ] Version history is immutable (no updates to past versions)
- [ ] Effective date resolution works correctly

### ServiceSupplier
- [ ] Supplier can be created with any of three types
- [ ] Supplier resolver respects marketplace model config
- [ ] `independent_only` config only returns independent providers
- [ ] `organization_only` config only returns organizations
- [ ] `hybrid` config returns all active suppliers
- [ ] Supplier status transitions follow the defined state machine
- [ ] Supplier events are emitted on lifecycle changes

### UI Kernel
- [ ] Base template renders with correct RTL direction
- [ ] Persian font (Vazirmatn) loads correctly
- [ ] Tailwind CSS compiles with all design tokens
- [ ] Portal layout renders sidebar on the right (RTL)
- [ ] Component templates (button, alert, card) render correctly
- [ ] Jalali date conversion works (ISO → Jalali display)
- [ ] Error pages (404, 500) render in Persian with correct layout

### API
- [ ] Responses include `X-Correlation-ID` header
- [ ] Errors follow Shared Error Model format
- [ ] Pagination returns correct structure
- [ ] Unauthenticated requests to protected endpoints return 401
- [ ] OpenAPI schema generates at `/api/v1/schema/`

---

## 10. Risk Mitigations

| Risk | Mitigation in Phase 1 |
|------|----------------------|
| Supplier abstraction leakage | Enforce through base model classes; no FK directly to "Organization" from order/assignment models |
| Tenant isolation failure | TenantAwareModel base class + middleware + queryset filtering; test every model |
| Event ordering issues | Outbox uses `created_at` ordering; each event has `occurred_at`; consumers handle out-of-order |
| Config resolution performance | Redis caching with TTL; lazy-load per request; batch preload for hot paths |
| Migration complexity | Single Django app for kernel; numbered migrations; seed data via management commands |
| RTL rendering bugs | Base template enforces `dir="rtl"`; component library tested with Persian content; Tailwind logical properties |

---

## Implementation Order Within Each Sprint

### Sprint 1 Execution Order:
1. Docker + docker-compose.yml
2. Django project scaffold (config/, apps/)
3. `pyproject.toml` + requirements
4. Settings (base, dev, test, prod)
5. Tenant model + TenantAwareModel base
6. User model (custom AbstractBaseUser)
7. RBAC models (Role, RoleAssignment, Permission)
8. Tenant middleware
9. Initial migrations
10. Management command: `seed_tenant`
11. Verify: `docker-compose up` → `migrate` → `seed_tenant` → Django admin accessible

### Sprint 2 Execution Order:
1. Event outbox model + publisher service
2. Outbox Celery task (publish_outbox_events)
3. Audit log model + audit service
4. Configuration models (key + value) + config resolver
5. Feature flag model + evaluation service
6. Policy models (definition + version) + policy service
7. ServiceSupplier model + supplier resolver
8. Marketplace config seeds (data migration)
9. Correlation middleware
10. Tests for all Sprint 2 deliverables

### Sprint 3 Execution Order:
1. Tailwind config (design tokens, fonts, colors, RTL)
2. PostCSS pipeline / Tailwind CLI build
3. Static files: Vazirmatn font, HTMX, Alpine.js
4. `base.html` template (RTL shell)
5. Layout templates (portal, admin, auth, public)
6. Component templates (button, alert, card, table, forms)
7. Jalali JS utility (app.js)
8. Error pages (404, 403, 500, maintenance)
9. Django template tags for common patterns
10. Visual smoke tests (render all components with Persian content)

### Sprint 4 Execution Order:
1. Base viewset + pagination + filters
2. Error handler (Shared Error Model)
3. API endpoints (health, config, flags, suppliers, audit)
4. OpenAPI schema configuration (drf-spectacular)
5. GitHub Actions CI workflow
6. Full test suite (all acceptance criteria)
7. Documentation (setup guide, architecture summary)
8. Final integration test (end-to-end: docker-compose up → seed → API calls → verify)

---

*End of Phase 1 Implementation Plan*
