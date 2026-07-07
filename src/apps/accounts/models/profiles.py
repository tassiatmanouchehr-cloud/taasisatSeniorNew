"""
Profile models for authentication and onboarding.

These are lightweight profile records created during registration.
They link to the kernel Person and UserAccount models.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ProfileStatus(models.TextChoices):
    """Profile lifecycle status."""

    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    DEACTIVATED = "deactivated", "Deactivated"


class CaregiverProviderType(models.TextChoices):
    """Caregiver affiliation type."""

    INDEPENDENT = "independent", "Independent"
    ORGANIZATION_AFFILIATED = "organization_affiliated", "Organization Affiliated"


class AffiliationStatus(models.TextChoices):
    """Company affiliation request status."""

    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class CustomerProfile(models.Model):
    """
    Customer/family profile created during registration.

    Links to kernel.UserAccount and kernel.Person.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    person = models.OneToOneField(
        "kernel.Person",
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    phone = models.CharField(max_length=20, db_index=True)
    display_name = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True)
    relation_to_elder = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ProfileStatus.choices,
        default=ProfileStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_customer_profile"

    def __str__(self):
        return f"Customer: {self.display_name} ({self.phone})"


class CaregiverProfile(models.Model):
    """
    Caregiver/provider profile created during registration.

    provider_type starts as 'independent'. Changes to 'organization_affiliated'
    only after company admin approves the affiliation request.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="caregiver_profile",
    )
    person = models.OneToOneField(
        "kernel.Person",
        on_delete=models.CASCADE,
        related_name="caregiver_profile",
    )
    phone = models.CharField(max_length=20, db_index=True)
    display_name = models.CharField(max_length=255)
    specialty = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    provider_type = models.CharField(
        max_length=30,
        choices=CaregiverProviderType.choices,
        default=CaregiverProviderType.INDEPENDENT,
    )
    status = models.CharField(
        max_length=20,
        choices=ProfileStatus.choices,
        default=ProfileStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_caregiver_profile"

    def __str__(self):
        return f"Caregiver: {self.display_name} ({self.specialty})"


class OrganizationProfile(models.Model):
    """
    Organization/company profile created during company admin registration.

    The admin_user is the first admin of this organization.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique organization code for caregiver affiliation requests.",
    )
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="administered_organizations",
    )
    company_type = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    team_size = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ProfileStatus.choices,
        default=ProfileStatus.ACTIVE,
    )
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.CASCADE,
        related_name="organizations",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_organization_profile"

    def __str__(self):
        return f"Org: {self.name} ({self.code})"


class CompanyAffiliationRequest(models.Model):
    """
    Pending request from a caregiver to affiliate with a company.

    Created during caregiver registration if company name/code is provided.
    Remains pending until company admin approves/rejects in a future sprint.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    caregiver_profile = models.ForeignKey(
        CaregiverProfile,
        on_delete=models.CASCADE,
        related_name="affiliation_requests",
    )
    requested_company_name_or_code = models.CharField(max_length=255)
    organization = models.ForeignKey(
        OrganizationProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="affiliation_requests",
        help_text="Resolved organization if code matched. Null if only name provided.",
    )
    status = models.CharField(
        max_length=20,
        choices=AffiliationStatus.choices,
        default=AffiliationStatus.PENDING,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_affiliations",
    )

    class Meta:
        db_table = "accounts_affiliation_request"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Affiliation: {self.caregiver_profile.display_name} → {self.requested_company_name_or_code} [{self.status}]"
