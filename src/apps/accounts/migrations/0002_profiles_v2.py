"""
Migration: extend profiles + add ElderProfile, TrustedContact,
OrganizationMembership, PlatformTeamMember.
"""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("kernel", "0008_service_supplier"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- CustomerProfile new fields ---
        migrations.AddField(
            model_name="customerprofile",
            name="preferred_contact_method",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(model_name="customerprofile", name="notes", field=models.TextField(blank=True, default="")),
        migrations.AddField(
            model_name="customerprofile", name="is_primary_family_contact", field=models.BooleanField(default=True)
        ),
        migrations.AddField(
            model_name="customerprofile", name="profile_completion_percent", field=models.IntegerField(default=0)
        ),
        # --- CaregiverProfile new fields ---
        migrations.AddField(
            model_name="caregiverprofile", name="profile_completion_percent", field=models.IntegerField(default=0)
        ),
        migrations.AddField(
            model_name="caregiverprofile",
            name="verification_status",
            field=models.CharField(
                choices=[
                    ("unverified", "Unverified"),
                    ("pending", "Pending"),
                    ("verified", "Verified"),
                    ("rejected", "Rejected"),
                ],
                default="unverified",
                max_length=20,
            ),
        ),
        migrations.AddField(model_name="caregiverprofile", name="bio", field=models.TextField(blank=True, default="")),
        migrations.AddField(
            model_name="caregiverprofile", name="years_experience", field=models.IntegerField(blank=True, null=True)
        ),
        migrations.AddField(
            model_name="caregiverprofile", name="service_radius_km", field=models.IntegerField(blank=True, null=True)
        ),
        # --- OrganizationProfile new fields ---
        migrations.AddField(
            model_name="organizationprofile",
            name="registration_number",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="organizationprofile", name="address", field=models.TextField(blank=True, default="")
        ),
        migrations.AddField(
            model_name="organizationprofile", name="description", field=models.TextField(blank=True, default="")
        ),
        migrations.AddField(
            model_name="organizationprofile",
            name="verification_status",
            field=models.CharField(
                choices=[
                    ("unverified", "Unverified"),
                    ("pending", "Pending"),
                    ("verified", "Verified"),
                    ("rejected", "Rejected"),
                ],
                default="unverified",
                max_length=20,
            ),
        ),
        # --- CompanyAffiliationRequest new fields ---
        migrations.AddField(
            model_name="companyaffiliationrequest", name="reviewer_note", field=models.TextField(blank=True, default="")
        ),
        migrations.AddField(
            model_name="companyaffiliationrequest",
            name="caregiver_note",
            field=models.TextField(blank=True, default=""),
        ),
        # --- CustomerProfile status choices update (add draft/archived) ---
        migrations.AlterField(
            model_name="customerprofile",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("active", "Active"),
                    ("suspended", "Suspended"),
                    ("archived", "Archived"),
                ],
                default="active",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="caregiverprofile",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("active", "Active"),
                    ("suspended", "Suspended"),
                    ("archived", "Archived"),
                ],
                default="active",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="organizationprofile",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("active", "Active"),
                    ("suspended", "Suspended"),
                    ("archived", "Archived"),
                ],
                default="active",
                max_length=20,
            ),
        ),
        # --- ElderProfile ---
        migrations.CreateModel(
            name="ElderProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("full_name", models.CharField(max_length=255)),
                ("gender", models.CharField(blank=True, max_length=20)),
                ("birth_date", models.DateField(blank=True, null=True)),
                ("approximate_age", models.IntegerField(blank=True, null=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("address", models.TextField(blank=True)),
                ("care_needs", models.TextField(blank=True)),
                ("medical_notes", models.TextField(blank=True)),
                (
                    "mobility_level",
                    models.CharField(
                        choices=[
                            ("independent", "Independent"),
                            ("needs_assistance", "Needs Assistance"),
                            ("wheelchair", "Wheelchair"),
                            ("bedridden", "Bedridden"),
                            ("unknown", "Unknown"),
                        ],
                        default="unknown",
                        max_length=30,
                    ),
                ),
                ("emergency_notes", models.TextField(blank=True)),
                ("is_primary", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("active", "Active"),
                            ("suspended", "Suspended"),
                            ("archived", "Archived"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "customer_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="elder_profiles",
                        to="accounts.customerprofile",
                    ),
                ),
            ],
            options={"db_table": "accounts_elder_profile"},
        ),
        # --- TrustedContact ---
        migrations.CreateModel(
            name="TrustedContact",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("full_name", models.CharField(max_length=255)),
                ("phone", models.CharField(max_length=20)),
                ("relation", models.CharField(blank=True, max_length=100)),
                ("can_receive_sms", models.BooleanField(default=True)),
                ("can_receive_emergency_notifications", models.BooleanField(default=False)),
                (
                    "access_level",
                    models.CharField(
                        choices=[
                            ("notify_only", "Notify Only"),
                            ("limited_view", "Limited View"),
                            ("coordinator", "Coordinator"),
                        ],
                        default="notify_only",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("active", "Active"),
                            ("suspended", "Suspended"),
                            ("archived", "Archived"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "customer_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trusted_contacts",
                        to="accounts.customerprofile",
                    ),
                ),
                (
                    "elder_profile",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="trusted_contacts",
                        to="accounts.elderprofile",
                    ),
                ),
            ],
            options={"db_table": "accounts_trusted_contact"},
        ),
        # --- OrganizationMembership ---
        migrations.CreateModel(
            name="OrganizationMembership",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "role_type",
                    models.CharField(
                        choices=[
                            ("admin", "Admin"),
                            ("operator", "Operator"),
                            ("caregiver", "Caregiver"),
                            ("accountant", "Accountant"),
                            ("support", "Support"),
                            ("manager", "Manager"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("pending", "Pending"),
                            ("suspended", "Suspended"),
                            ("removed", "Removed"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("joined_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="accounts.organizationprofile",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="org_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="org_memberships",
                        to="kernel.person",
                    ),
                ),
                (
                    "invited_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "accounts_organization_membership",
                "unique_together": {("organization", "user", "role_type")},
            },
        ),
        # --- PlatformTeamMember ---
        migrations.CreateModel(
            name="PlatformTeamMember",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "team_area",
                    models.CharField(
                        choices=[
                            ("owner", "Owner"),
                            ("support", "Support"),
                            ("operations", "Operations"),
                            ("marketing", "Marketing"),
                            ("accounting", "Accounting"),
                            ("security", "Security"),
                            ("it", "IT"),
                            ("admin", "Admin"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("suspended", "Suspended"), ("removed", "Removed")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="platform_team_member",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="platform_team_memberships",
                        to="kernel.person",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "accounts_platform_team_member"},
        ),
    ]
