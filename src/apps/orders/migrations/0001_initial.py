"""Initial migration for orders app — catalog + order models."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0002_profiles_v2"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceCategory",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True)),
                ("icon", models.CharField(blank=True, max_length=50)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("inactive", "Inactive")], default="active", max_length=20
                    ),
                ),
                ("sort_order", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "orders_service_category",
                "ordering": ["sort_order", "name"],
                "verbose_name_plural": "Service Categories",
            },
        ),
        migrations.CreateModel(
            name="ServiceType",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("base_duration_minutes", models.IntegerField(blank=True, null=True)),
                ("requires_elder_profile", models.BooleanField(default=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("inactive", "Inactive")], default="active", max_length=20
                    ),
                ),
                ("sort_order", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_types",
                        to="orders.servicecategory",
                    ),
                ),
            ],
            options={
                "db_table": "orders_service_type",
                "ordering": ["sort_order", "name"],
                "unique_together": {("category", "slug")},
            },
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("order_number", models.CharField(db_index=True, max_length=30, unique=True)),
                (
                    "source",
                    models.CharField(
                        choices=[("public", "Public/Customer"), ("operator", "Operator/Phone")], max_length=20
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            (
                                "pending_operator_review",
                                "\u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631 \u062a\u0627\u06cc\u06cc\u062f \u0627\u067e\u0631\u0627\u062a\u0648\u0631",
                            ),
                            ("new", "\u062c\u062f\u06cc\u062f"),
                            (
                                "waiting_service",
                                "\u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631 \u0627\u0646\u062c\u0627\u0645 \u062e\u062f\u0645\u062a",
                            ),
                            (
                                "in_progress",
                                "\u062f\u0631 \u062d\u0627\u0644 \u0627\u0646\u062c\u0627\u0645 \u062e\u062f\u0645\u062a",
                            ),
                            ("completed", "\u0627\u0646\u062c\u0627\u0645 \u0634\u062f\u0647"),
                            ("cancellation_requested", "\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0644\u063a\u0648"),
                            ("cancelled", "\u0644\u063a\u0648 \u0634\u062f\u0647"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                ("description", models.TextField()),
                ("city", models.CharField(max_length=100)),
                ("address", models.TextField()),
                ("phone", models.CharField(max_length=20)),
                ("scheduled_for", models.DateTimeField(blank=True, null=True)),
                ("requested_date", models.DateField(blank=True, null=True)),
                ("requested_time_window", models.CharField(blank=True, max_length=100)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("cancellation_reason", models.TextField(blank=True)),
                ("internal_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "service_category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="orders.servicecategory"
                    ),
                ),
                (
                    "service_type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="orders",
                        to="orders.servicetype",
                    ),
                ),
                (
                    "customer_profile",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="orders",
                        to="accounts.customerprofile",
                    ),
                ),
                (
                    "elder_profile",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="orders",
                        to="accounts.elderprofile",
                    ),
                ),
                (
                    "trusted_contact",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="orders",
                        to="accounts.trustedcontact",
                    ),
                ),
                (
                    "assigned_provider",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_orders",
                        to="accounts.caregiverprofile",
                    ),
                ),
                (
                    "assigned_organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_orders",
                        to="accounts.organizationprofile",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "cancellation_requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "orders_order", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="OrderStatusHistory",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("from_status", models.CharField(blank=True, max_length=30)),
                ("to_status", models.CharField(max_length=30)),
                ("reason", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="status_history", to="orders.order"
                    ),
                ),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={"db_table": "orders_status_history", "ordering": ["-created_at"]},
        ),
    ]
