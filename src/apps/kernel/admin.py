"""
Django admin registration for Kernel models.

All kernel models are registered here for administrative access.
Admin is available at /admin/ for platform staff.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Permission, Person, Role, RoleAssignment, Tenant, UserAccount


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["name", "slug", "domain"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ["full_name", "tenant", "status", "created_at"]
    list_filter = ["status", "tenant"]
    search_fields = ["full_name"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]


@admin.register(UserAccount)
class UserAccountAdmin(BaseUserAdmin):
    list_display = ["email", "phone", "person", "tenant", "is_active", "is_staff", "date_joined"]
    list_filter = ["is_active", "is_staff", "is_superuser", "tenant"]
    search_fields = ["email", "phone"]
    readonly_fields = ["id", "date_joined", "last_login"]
    ordering = ["-date_joined"]

    # Override fieldsets since we don't use username
    fieldsets = (
        (None, {"fields": ("id", "email", "phone", "password")}),
        ("Personal", {"fields": ("person", "tenant")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "phone", "password1", "password2", "person", "tenant", "is_staff"),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "tenant", "is_system", "created_at"]
    list_filter = ["is_system", "tenant"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["key", "module_id", "resource_type", "action", "requires_scope", "audit_required"]
    list_filter = ["module_id", "requires_scope", "audit_required"]
    search_fields = ["key", "description"]
    readonly_fields = ["id", "created_at"]


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "scope_type", "is_active", "granted_at", "expires_at"]
    list_filter = ["is_active", "scope_type", "role", "tenant"]
    search_fields = ["user__email", "role__name"]
    readonly_fields = ["id", "granted_at"]
