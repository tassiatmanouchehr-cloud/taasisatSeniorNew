"""
Core Profile-ServiceSupplier Invariant Remediation, Phase 7.

Adds a database-level uniqueness constraint on
(linked_entity_id, linked_entity_type) — the invariant `get_or_create()`
alone can never guarantee under concurrent writes (see
apps.kernel.services.supplier_registry.SupplierRegistry.get_or_create_supplier()).
Depends on 0012_reconcile_profile_supplier_data, which must resolve any
existing duplicate/missing/drifted rows first — this constraint is only
safe to add once that data is clean.

Replaces the former plain idx_supplier_linked_entity index: a
UniqueConstraint is backed by PostgreSQL with its own unique index over
the same two columns, so keeping the old plain index alongside it would
be redundant.

Hand-written rather than accepted verbatim from `makemigrations` — this
repository has documented, pre-existing, unrelated `makemigrations
--check` drift across nearly every kernel model (see
`project docs/traceability/OPEN_QUESTIONS_AND_RISKS.md` RISK-009: cosmetic
Django-version-skew field-kwarg noise, not a real schema difference). Only
the two operations that are an actual, intended change of this migration
are included here.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kernel", "0012_reconcile_profile_supplier_data"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="servicesupplier",
            name="idx_supplier_linked_entity",
        ),
        migrations.AddConstraint(
            model_name="servicesupplier",
            constraint=models.UniqueConstraint(
                fields=("linked_entity_id", "linked_entity_type"),
                name="uniq_supplier_linked_entity",
            ),
        ),
    ]
