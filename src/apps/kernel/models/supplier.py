"""
ServiceSupplier model.

Universal abstraction for any entity that can receive, accept, fulfill,
or be financially credited for a service order. All business modules
reference ServiceSupplier — never Organization or Provider directly.

Supplier types:
- INDEPENDENT_PROVIDER: Provider working without organization affiliation
- ORGANIZATION: Company, agency, clinic, studio, contractor group
- ORGANIZATION_PROVIDER: Provider affiliated with an organization

The platform supports three marketplace models by configuration only:
- independent_only: Only independent providers active
- organization_only: Only organizations active
- hybrid: Both types coexist

References:
- ADR-001.03 (ServiceSupplier abstraction mandatory)
- ADR-001.04 (Three marketplace models by config)
- ADR-001.24 (Supplier-based matching/assignment/financial/review/notification)
- Architecture Intake Report Section 16 (Supplier Abstraction Layer)
- Phase 0.5 Deliverable 1, Section 1.1 (ServiceSupplier entity)
- Phase 0.5 Deliverable 11 (Supplier Aggregate: root=ServiceSupplier)
"""

import uuid

from django.db import models
from django.utils import timezone


class SupplierType(models.TextChoices):
    """Service supplier types per Architecture Intake Report Section 16."""

    INDEPENDENT_PROVIDER = "INDEPENDENT_PROVIDER", "Independent Provider"
    ORGANIZATION = "ORGANIZATION", "Organization"
    ORGANIZATION_PROVIDER = "ORGANIZATION_PROVIDER", "Organization Provider"


class SupplierStatus(models.TextChoices):
    """Supplier lifecycle states per Phase 0.5 Deliverable 12."""

    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    DEACTIVATED = "deactivated", "Deactivated"


class AvailabilityStatus(models.TextChoices):
    """Real-time availability indicator."""

    AVAILABLE = "available", "Available"
    BUSY = "busy", "Busy"
    OFFLINE = "offline", "Offline"
    ON_LEAVE = "on_leave", "On Leave"


class VerificationLevel(models.TextChoices):
    """Progressive verification levels per Phase 0.5 Deliverable 2."""

    UNVERIFIED = "unverified", "Unverified"
    BASIC = "basic", "Basic"
    ADVANCED = "advanced", "Advanced"
    PREMIUM = "premium", "Premium"


class ServiceSupplier(models.Model):
    """
    Universal supply-side abstraction.

    Every order, assignment, matching result, financial payable, review,
    and notification target references this entity. Business modules
    NEVER directly reference Organization or IndependentProvider for
    business operations — they use ServiceSupplier.

    The linked_entity_id/type pattern links to the actual identity entity
    (IndependentProviderProfile, Organization, OrganizationProviderProfile)
    which lives in Module 08 (Phase 2).

    Per ADR-001.03: ServiceSupplier is mandatory.
    Per ADR-001.04: Three marketplace models without schema change.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.PROTECT, related_name="service_suppliers",
    )

    # Type classification
    supplier_type = models.CharField(
        max_length=30,
        choices=SupplierType.choices,
        db_index=True,
        help_text="What kind of supplier this is.",
    )

    # Link to identity entity (Module 08 owns the actual profiles)
    linked_entity_id = models.UUIDField(
        help_text="ID of the linked identity entity (profile or organization).",
    )
    linked_entity_type = models.CharField(
        max_length=100,
        help_text="Type of linked entity: 'IndependentProviderProfile', 'Organization', 'OrganizationProviderProfile'.",
    )

    # Display
    display_name = models.CharField(
        max_length=255,
        help_text="Human-readable name for UI display (resolved from linked entity).",
    )

    # Lifecycle
    status = models.CharField(
        max_length=20,
        choices=SupplierStatus.choices,
        default=SupplierStatus.PENDING,
        db_index=True,
    )

    # Capabilities (what this supplier can do)
    capabilities = models.JSONField(
        default=dict,
        blank=True,
        help_text="Supplier capabilities (schema-validated, links to Capability entities).",
    )
    service_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="Service category IDs this supplier serves.",
    )

    # Real-time state
    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.OFFLINE,
    )

    # Verification
    verification_level = models.CharField(
        max_length=20,
        choices=VerificationLevel.choices,
        default=VerificationLevel.UNVERIFIED,
    )

    # Financial identity link (Module 05)
    financial_party_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Link to FinancialParty in Module 05 (created when supplier activates).",
    )

    # Reputation (cached from Module 06/14)
    reputation_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cached reputation score (updated by Module 06/14 events).",
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    external_ref = models.CharField(
        max_length=255,
        blank=True,
        help_text="External reference ID (for integrations).",
    )

    # Standard fields
    module_id = models.CharField(max_length=10, default="M25")
    entity_type = models.CharField(max_length=100, default="ServiceSupplier")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'kernel"."service_supplier'
        verbose_name = "Service Supplier"
        verbose_name_plural = "Service Suppliers"
        ordering = ["display_name"]
        indexes = [
            models.Index(
                fields=["tenant", "supplier_type", "status"],
                name="idx_supplier_tenant_type_st",
            ),
            models.Index(
                fields=["tenant", "status", "availability_status"],
                name="idx_supplier_availability",
            ),
            models.Index(
                fields=["linked_entity_id", "linked_entity_type"],
                name="idx_supplier_linked_entity",
            ),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.get_supplier_type_display()}) [{self.status}]"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.version += 1
        super().save(*args, **kwargs)

    def activate(self):
        """Transition supplier to active status."""
        if self.status not in (SupplierStatus.PENDING, SupplierStatus.SUSPENDED):
            raise ValueError(
                f"Cannot activate supplier in '{self.status}' status. "
                f"Only pending or suspended suppliers can be activated."
            )
        self.status = SupplierStatus.ACTIVE
        self.save(update_fields=["status", "updated_at", "version"])

    def suspend(self):
        """Transition supplier to suspended status."""
        if self.status != SupplierStatus.ACTIVE:
            raise ValueError("Only active suppliers can be suspended.")
        self.status = SupplierStatus.SUSPENDED
        self.save(update_fields=["status", "updated_at", "version"])

    def restore(self):
        """Restore a suspended supplier to active status."""
        if self.status != SupplierStatus.SUSPENDED:
            raise ValueError("Only suspended suppliers can be restored.")
        self.status = SupplierStatus.ACTIVE
        self.save(update_fields=["status", "updated_at", "version"])

    def deactivate(self):
        """Permanently deactivate a supplier."""
        if self.status not in (SupplierStatus.ACTIVE, SupplierStatus.SUSPENDED):
            raise ValueError("Only active or suspended suppliers can be deactivated.")
        self.status = SupplierStatus.DEACTIVATED
        self.save(update_fields=["status", "updated_at", "version"])
