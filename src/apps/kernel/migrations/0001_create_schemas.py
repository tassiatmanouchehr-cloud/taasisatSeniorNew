"""
Create all PostgreSQL schemas for the Enterprise Service Marketplace Platform.

Per ADR-001.18 and Deliverable 15 of the Phase 0.5 Domain Model Freeze,
all tables live in named schemas — never in the public schema.

This migration creates all 23 schemas required by the platform.
It must run before any model migration that targets a non-public schema.
"""

from django.db import migrations

# All 23 schemas per PHASE_0_5_ENTERPRISE_DOMAIN_MODEL_FREEZE.md Deliverable 15
SCHEMAS = [
    "kernel",
    "identity",
    "organizations",
    "catalog",
    "availability",
    "pricing",
    "marketplace",
    "orders",
    "execution",
    "financial",
    "communication",
    "trust",
    "documents",
    "incentives",
    "search",
    "geospatial",
    "analytics",
    "integration",
    "workflow",
    "jobs",
    "observability",
    "localization",
    "audit",
]

# Forward: create all schemas
CREATE_SQL = "\n".join(
    f"CREATE SCHEMA IF NOT EXISTS {schema};" for schema in SCHEMAS
)

# Reverse: drop all schemas (only safe in development/testing)
DROP_SQL = "\n".join(
    f"DROP SCHEMA IF EXISTS {schema} CASCADE;" for schema in reversed(SCHEMAS)
)


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=CREATE_SQL,
            reverse_sql=DROP_SQL,
        ),
    ]
