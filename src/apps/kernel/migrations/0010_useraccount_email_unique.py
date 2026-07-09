"""
Module 21A: UserAccount.email becomes the auth USERNAME_FIELD.

Existing rows store "" for accounts with no email (phone-only OTP
accounts) — a hard unique constraint on "" would collide the moment a
second such account exists. Step 1 converts existing "" to NULL (Postgres
allows any number of NULLs under a unique constraint); step 2 then adds
null=True, unique=True.
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
        migrations.RunPython(blank_email_to_null, null_email_to_blank),
        migrations.AlterField(
            model_name="useraccount",
            name="email",
            field=models.EmailField(blank=True, max_length=255, null=True, unique=True),
        ),
    ]
