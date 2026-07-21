"""
Module 21A: UserAccount.email becomes the auth USERNAME_FIELD.

Existing rows store "" for accounts with no email (phone-only OTP
accounts) — a hard unique constraint on "" would collide the moment a
second such account exists. The column must allow NULL *before* any row
is converted to NULL (the original single-step ordering ran the data
migration first, which raises IntegrityError against the still-NOT-NULL
column on any database with a pre-existing blank-email row), and the
unique constraint can only be added *after* every "" has been converted
(otherwise the not-yet-deduplicated "" values collide against each
other). Three ordered steps: (1) allow NULL, still non-unique; (2)
convert existing "" to NULL (Postgres allows any number of NULLs under a
unique constraint); (3) add the unique constraint.

Step 3 uses SeparateDatabaseAndState rather than a plain AlterField, for
the same reason as kernel.0011's fix: UserAccount.Meta.db_table is a
schema-qualification hack ("kernel\".\"user_account") that places this
table inside the "kernel" Postgres schema. A plain AlterField's reverse
path relies on introspecting the database to find the unique constraint
and LIKE-pattern index it needs to drop, and that introspection (and
Django's generated DROP INDEX reverse SQL) resolves unqualified names
against search_path (default "$user", public), which does not include
"kernel" — the constraint/index are never found, the DROP silently
no-ops, and a subsequent re-apply fails with "already exists" even
though migration state correctly shows 0010 as unapplied. Verified
directly: `sqlmigrate kernel 0010 --backwards` before this fix showed
only an unqualified `DROP INDEX IF EXISTS` for the LIKE index and no
statement at all for the unique constraint. state_operations keeps a
plain AlterField for Django's own model-state tracking; database_
operations performs the actual schema change with explicit,
schema-qualified SQL in both directions, using the exact constraint/
index names Django's own forward SQL already generates.
"""

from django.db import migrations, models


def blank_email_to_null(apps, schema_editor):
    UserAccount = apps.get_model("kernel", "UserAccount")
    UserAccount.objects.filter(email="").update(email=None)


def null_email_to_blank(apps, schema_editor):
    UserAccount = apps.get_model("kernel", "UserAccount")
    UserAccount.objects.filter(email__isnull=True).update(email="")


class Migration(migrations.Migration):
    dependencies = [
        ("kernel", "0009_servicesupplier_tenant_fk"),
    ]

    operations = [
        migrations.AlterField(
            model_name="useraccount",
            name="email",
            field=models.EmailField(blank=True, max_length=255, null=True),
        ),
        migrations.RunPython(blank_email_to_null, null_email_to_blank),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="useraccount",
                    name="email",
                    field=models.EmailField(blank=True, max_length=255, null=True, unique=True),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "kernel"."user_account" '
                        'ADD CONSTRAINT "user_account_email_d74bf2f6_uniq" UNIQUE ("email");\n'
                        'CREATE INDEX "user_account_email_d74bf2f6_like" '
                        'ON "kernel"."user_account" ("email" varchar_pattern_ops);'
                    ),
                    reverse_sql=(
                        'DROP INDEX IF EXISTS "kernel"."user_account_email_d74bf2f6_like";\n'
                        'ALTER TABLE "kernel"."user_account" '
                        'DROP CONSTRAINT IF EXISTS "user_account_email_d74bf2f6_uniq";'
                    ),
                ),
            ],
        ),
    ]
