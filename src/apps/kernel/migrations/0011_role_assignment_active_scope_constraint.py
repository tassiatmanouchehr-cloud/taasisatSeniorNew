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
#
# Architecture Review remediation (Epic 04, PR #28 required remediation
# item 1): plain migrations.AddConstraint's auto-reverse is broken for this
# specific table. RoleAssignment.Meta.db_table is a schema-qualification
# hack ("kernel\".\"role_assignment") that places the table (and therefore
# this partial unique index — Postgres has no ADD CONSTRAINT ... UNIQUE ...
# WHERE, so Django implements a conditional UniqueConstraint as a raw
# CREATE UNIQUE INDEX) inside the "kernel" Postgres schema. Django's
# generated forward SQL schema-qualifies the TABLE reference
# ("kernel"."role_assignment"), so CREATE UNIQUE INDEX succeeds regardless
# of search_path. Its generated reverse SQL only names the INDEX itself
# (DROP INDEX IF EXISTS "uq_role_assignment_active_scope";), unqualified —
# Postgres resolves that against search_path (default "$user", public"),
# which does not include "kernel", so the DROP silently no-ops (IF EXISTS
# suppresses the "not found" error) while Django's own migration-state
# bookkeeping still records 0011 as unapplied. The constraint is left
# physically in place, and a subsequent forward re-apply then fails with
# "relation ... already exists". Verified directly: `sqlmigrate kernel 0011
# --backwards` before this fix showed the unqualified DROP INDEX; a manual
# psql DROP INDEX IF EXISTS "uq_role_assignment_active_scope" (unqualified,
# default search_path) against a database where the index actually exists
# in the kernel schema reproduces the silent no-op exactly.
#
# Fix: SeparateDatabaseAndState keeps Django's model-state tracking
# (state_operations: the same AddConstraint as before, so
# makemigrations/model introspection see this constraint exactly as they
# did previously — no behavior change to the model or to forward
# deployment) while replacing the actual database SQL with an explicit
# RunSQL pair that schema-qualifies the index name in both directions, so
# neither direction depends on search_path.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kernel", "0010_useraccount_email_unique"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddConstraint(
                    model_name="roleassignment",
                    constraint=models.UniqueConstraint(
                        condition=models.Q(("is_active", True)),
                        fields=("tenant", "user", "role", "scope_type", "scope_id"),
                        name="uq_role_assignment_active_scope",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'CREATE UNIQUE INDEX "uq_role_assignment_active_scope" '
                        'ON "kernel"."role_assignment" '
                        '("tenant_id", "user_id", "role_id", "scope_type", "scope_id") '
                        'WHERE "is_active";'
                    ),
                    reverse_sql='DROP INDEX IF EXISTS "kernel"."uq_role_assignment_active_scope";',
                ),
            ],
        ),
    ]
