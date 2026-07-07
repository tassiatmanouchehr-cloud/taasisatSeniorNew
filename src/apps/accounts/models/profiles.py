"""
Profile models for the marketplace domain.

Models: CustomerProfile, ElderProfile, TrustedContact, CaregiverProfile,
OrganizationProfile, OrganizationMembership, CompanyAffiliationRequest,
PlatformTeamMember.
"""

import uuid

from django.conf import settings
from django.db import models


class ProfileStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    ARCHIVED = "archived", "Archived"


class CaregiverProviderType(models.TextChoices):
    INDEPENDENT = "independent", "Independent"
    ORGANIZATION_AFFILIATED = "organization_affiliated", "Organization Affiliated"


class VerificationStatus(models.TextChoices):
    UNVERIFIED = "unverified", "Unverified"
    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"


class AffiliationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class MobilityLevel(models.TextChoices):
    INDEPENDENT = "independent", "Independent"
    NEEDS_ASSISTANCE = "needs_assistance", "Needs Assistance"
    WHEELCHAIR = "wheelchair", "Wheelchair"
    BEDRIDDEN = "bedridden", "Bedridden"
    UNKNOWN = "unknown", "Unknown"


class TrustedContactAccessLevel(models.TextChoices):
    NOTIFY_ONLY = "notify_only", "Notify Only"
    LIMITED_VIEW = "limited_view", "Limited View"
    COORDINATOR = "coordinator", "Coordinator"


class OrgMembershipRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    OPERATOR = "operator", "Operator"
    CAREGIVER = "caregiver", "Caregiver"
    ACCOUNTANT = "accountant", "Accountant"
    SUPPORT = "support", "Support"
    MANAGER = "manager", "Manager"


class OrgMembershipStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PENDING = "pending", "Pending"
    SUSPENDED = "suspended", "Suspended"
    REMOVED = "removed", "Removed"


class PlatformTeamArea(models.TextChoices):
    OWNER = "owner", "Owner"
    SUPPORT = "support", "Support"
    OPERATIONS = "operations", "Operations"
    MARKETING = "marketing", "Marketing"
    ACCOUNTING = "accounting", "Accounting"
    SECURITY = "security", "Security"
    IT = "it", "IT"
    ADMIN = "admin", "Admin"


class PlatformTeamStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    REMOVED = "removed", "Removed"


# ============================================================
# CustomerProfile
# ============================================================

class CustomerProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_profile",
    )
    person = models.OneToOneField(
        "kernel.Person", on_delete=models.CASCADE, related_name="customer_profile",
    )
    phone = models.CharField(max_length=20, db_index=True)
    display_name = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True)
    relation_to_elder = models.CharField(max_length=50, blank=True)
    preferred_contact_method = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    is_primary_family_contact = models.BooleanField(default=True)
    profile_completion_percent = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=ProfileStatus.choices, default=ProfileStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_customer_profile"

    def __str__(self):
        return f"Customer: {self.display_name} ({self.phone})"


# ============================================================
# ElderProfile
# ============================================================

class ElderProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_profile = models.ForeignKey(
        CustomerProfile, on_delete=models.CASCADE, related_name="elder_profiles",
    )
    full_name = models.CharField(max_length=255)
    gender = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    approximate_age = models.IntegerField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    care_needs = models.TextField(blank=True)
    medical_notes = models.TextField(blank=True)
    mobility_level = models.CharField(
        max_length=30, choices=MobilityLevel.choices, default=MobilityLevel.UNKNOWN,
    )
    emergency_notes = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=ProfileStatus.choices, default=ProfileStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_elder_profile"

    def __str__(self):
        return f"Elder: {self.full_name} (customer={self.customer_profile.display_name})"


# ============================================================
# TrustedContact
# ============================================================

class TrustedContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_profile = models.ForeignKey(
        CustomerProfile, on_delete=models.CASCADE, related_name="trusted_contacts",
    )
    elder_profile = models.ForeignKey(
        ElderProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="trusted_contacts",
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    relation = models.CharField(max_length=100, blank=True)
    can_receive_sms = models.BooleanField(default=True)
    can_receive_emergency_notifications = models.BooleanField(default=False)
    access_level = models.CharField(
        max_length=20, choices=TrustedContactAccessLevel.choices, default=TrustedContactAccessLevel.NOTIFY_ONLY,
    )
    status = models.CharField(max_length=20, choices=ProfileStatus.choices, default=ProfileStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_trusted_contact"

    def __str__(self):
        return f"Contact: {self.full_name} ({self.phone})"


# ============================================================
# CaregiverProfile
# ============================================================

class CaregiverProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="caregiver_profile",
    )
    person = models.OneToOneField(
        "kernel.Person", on_delete=models.CASCADE, related_name="caregiver_profile",
    )
    phone = models.CharField(max_length=20, db_index=True)
    display_name = models.CharField(max_length=255)
    specialty = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    provider_type = models.CharField(
        max_length=30, choices=CaregiverProviderType.choices, default=CaregiverProviderType.INDEPENDENT,
    )
    profile_completion_percent = models.IntegerField(default=0)
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.UNVERIFIED,
    )
    bio = models.TextField(blank=True)
    years_experience = models.IntegerField(null=True, blank=True)
    service_radius_km = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ProfileStatus.choices, default=ProfileStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_caregiver_profile"

    def __str__(self):
        return f"Caregiver: {self.display_name} ({self.specialty})"


# ============================================================
# OrganizationProfile
# ============================================================

class OrganizationProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="administered_organizations",
    )
    company_type = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    team_size = models.CharField(max_length=20, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True)
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.UNVERIFIED,
    )
    status = models.CharField(max_length=20, choices=ProfileStatus.choices, default=ProfileStatus.ACTIVE)
    tenant = models.ForeignKey(
        "kernel.Tenant", on_delete=models.CASCADE, related_name="organizations", null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_organization_profile"

    def __str__(self):
        return f"Org: {self.name} ({self.code})"


# ============================================================
# OrganizationMembership
# ============================================================

class OrganizationMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        OrganizationProfile, on_delete=models.CASCADE, related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="org_memberships",
    )
    person = models.ForeignKey(
        "kernel.Person", on_delete=models.SET_NULL, null=True, blank=True, related_name="org_memberships",
    )
    role_type = models.CharField(max_length=20, choices=OrgMembershipRole.choices)
    status = models.CharField(
        max_length=20, choices=OrgMembershipStatus.choices, default=OrgMembershipStatus.ACTIVE,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_organization_membership"
        unique_together = [("organization", "user", "role_type")]

    def __str__(self):
        return f"{self.user} → {self.organization.name} ({self.role_type})"


# ============================================================
# CompanyAffiliationRequest
# ============================================================

class CompanyAffiliationRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    caregiver_profile = models.ForeignKey(
        CaregiverProfile, on_delete=models.CASCADE, related_name="affiliation_requests",
    )
    requested_company_name_or_code = models.CharField(max_length=255)
    organization = models.ForeignKey(
        OrganizationProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="affiliation_requests",
    )
    status = models.CharField(max_length=20, choices=AffiliationStatus.choices, default=AffiliationStatus.PENDING)
    reviewer_note = models.TextField(blank=True)
    caregiver_note = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_affiliations",
    )

    class Meta:
        db_table = "accounts_affiliation_request"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Affiliation: {self.caregiver_profile.display_name} → {self.requested_company_name_or_code} [{self.status}]"


# ============================================================
# PlatformTeamMember
# ============================================================

class PlatformTeamMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="platform_team_member",
    )
    person = models.ForeignKey(
        "kernel.Person", on_delete=models.CASCADE, related_name="platform_team_memberships",
    )
    team_area = models.CharField(max_length=20, choices=PlatformTeamArea.choices)
    status = models.CharField(
        max_length=20, choices=PlatformTeamStatus.choices, default=PlatformTeamStatus.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_platform_team_member"

    def __str__(self):
        return f"Team: {self.person.full_name} ({self.team_area})"
