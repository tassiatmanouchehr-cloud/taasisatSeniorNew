# Hand-written (not the raw `makemigrations` output): the auto-generated
# migration also included ~79 unrelated operations (AlterField for
# help_text/verbose_name drift, RenameIndex) from the documented Django-
# version-skew "phantom migration" issue (see
# docs/architecture/technical-debt-register.md). One of those RenameIndex
# operations referenced an index name that does not match the actual
# database state and fails to apply. Kept only the one real, intentional
# operation for this Epic — the same discipline used for
# finance/migrations/0002_settlement_idempotency_constraints.py (Epic 03
# Sprint 1).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kernel", "0010_useraccount_email_unique"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="roleassignment",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_active", True)),
                fields=("tenant", "user", "role", "scope_type", "scope_id"),
                name="uq_role_assignment_active_scope",
            ),
        ),
    ]
