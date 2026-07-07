"""Django admin registration for accounts models."""

from django.contrib import admin

from .models import (
    CaregiverProfile,
    CompanyAffiliationRequest,
    CustomerProfile,
    ElderProfile,
    OrganizationMembership,
    OrganizationProfile,
    OTPChallenge,
    PlatformTeamMember,
    TrustedContact,
)


@admin.register(OTPChallenge)
class OTPChallengeAdmin(admin.ModelAdmin):
    list_display = ["phone", "purpose", "created_at", "expires_at", "attempts", "consumed_at"]
    list_filter = ["purpose"]
    search_fields = ["phone"]
    readonly_fields = ["id", "code_hash", "created_at"]


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ["display_name", "phone", "city", "status", "profile_completion_percent", "created_at"]
    list_filter = ["status", "city"]
    search_fields = ["display_name", "phone"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(ElderProfile)
class ElderProfileAdmin(admin.ModelAdmin):
    list_display = ["full_name", "customer_profile", "city", "mobility_level", "is_primary", "status"]
    list_filter = ["status", "mobility_level", "is_primary"]
    search_fields = ["full_name"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(TrustedContact)
class TrustedContactAdmin(admin.ModelAdmin):
    list_display = ["full_name", "phone", "customer_profile", "access_level", "status"]
    list_filter = ["access_level", "status"]
    search_fields = ["full_name", "phone"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CaregiverProfile)
class CaregiverProfileAdmin(admin.ModelAdmin):
    list_display = ["display_name", "phone", "specialty", "provider_type", "verification_status", "status"]
    list_filter = ["provider_type", "verification_status", "status", "city"]
    search_fields = ["display_name", "phone", "specialty"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(OrganizationProfile)
class OrganizationProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "company_type", "city", "verification_status", "status"]
    list_filter = ["verification_status", "status", "company_type"]
    search_fields = ["name", "code", "city"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "role_type", "status", "joined_at"]
    list_filter = ["role_type", "status"]
    search_fields = ["user__phone", "organization__name"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CompanyAffiliationRequest)
class CompanyAffiliationRequestAdmin(admin.ModelAdmin):
    list_display = ["caregiver_profile", "requested_company_name_or_code", "organization", "status", "requested_at"]
    list_filter = ["status"]
    search_fields = ["requested_company_name_or_code", "caregiver_profile__display_name"]
    readonly_fields = ["id", "requested_at", "reviewed_at"]


@admin.register(PlatformTeamMember)
class PlatformTeamMemberAdmin(admin.ModelAdmin):
    list_display = ["person", "team_area", "status", "created_at"]
    list_filter = ["team_area", "status"]
    search_fields = ["person__full_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
