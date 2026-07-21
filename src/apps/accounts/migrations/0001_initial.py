"""
Initial migration for accounts app.

Creates: OTPChallenge, CustomerProfile, CaregiverProfile,
         OrganizationProfile, CompanyAffiliationRequest.

Run: python manage.py migrate accounts
"""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("kernel", "0008_service_supplier"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # OTPChallenge
        migrations.CreateModel(
            name="OTPChallenge",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("phone", models.CharField(db_index=True, max_length=20)),
                (
                    "purpose",
                    models.CharField(
                        choices=[("login", "Login"), ("register", "Register")], default="login", max_length=20
                    ),
                ),
                ("code_hash", models.CharField(help_text="SHA-256 hash of the OTP code.", max_length=128)),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("attempts", models.IntegerField(default=0)),
                ("max_attempts", models.IntegerField(default=5)),
                ("request_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "accounts_otp_challenge",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="otpchallenge",
            index=models.Index(fields=["phone", "purpose", "-created_at"], name="idx_otp_phone_purpose"),
        ),
        # CustomerProfile
        migrations.CreateModel(
            name="CustomerProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("phone", models.CharField(db_index=True, max_length=20)),
                ("display_name", models.CharField(max_length=255)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("relation_to_elder", models.CharField(blank=True, max_length=50)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("suspended", "Suspended"), ("deactivated", "Deactivated")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "person",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="customer_profile", to="kernel.person"
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="customer_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "accounts_customer_profile",
            },
        ),
        # CaregiverProfile
        migrations.CreateModel(
            name="CaregiverProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("phone", models.CharField(db_index=True, max_length=20)),
                ("display_name", models.CharField(max_length=255)),
                ("specialty", models.CharField(blank=True, max_length=100)),
                ("city", models.CharField(blank=True, max_length=100)),
                (
                    "provider_type",
                    models.CharField(
                        choices=[
                            ("independent", "Independent"),
                            ("organization_affiliated", "Organization Affiliated"),
                        ],
                        default="independent",
                        max_length=30,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("suspended", "Suspended"), ("deactivated", "Deactivated")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "person",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="caregiver_profile",
                        to="kernel.person",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="caregiver_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "accounts_caregiver_profile",
            },
        ),
        # OrganizationProfile
        migrations.CreateModel(
            name="OrganizationProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                (
                    "code",
                    models.CharField(
                        db_index=True,
                        help_text="Unique organization code for caregiver affiliation requests.",
                        max_length=50,
                        unique=True,
                    ),
                ),
                ("company_type", models.CharField(blank=True, max_length=100)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("team_size", models.CharField(blank=True, max_length=20)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("suspended", "Suspended"), ("deactivated", "Deactivated")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "admin_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="administered_organizations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="organizations",
                        to="kernel.tenant",
                    ),
                ),
            ],
            options={
                "db_table": "accounts_organization_profile",
            },
        ),
        # CompanyAffiliationRequest
        migrations.CreateModel(
            name="CompanyAffiliationRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("requested_company_name_or_code", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "caregiver_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="affiliation_requests",
                        to="accounts.caregiverprofile",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        help_text="Resolved organization if code matched.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="affiliation_requests",
                        to="accounts.organizationprofile",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_affiliations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "accounts_affiliation_request",
                "ordering": ["-requested_at"],
            },
        ),
    ]
