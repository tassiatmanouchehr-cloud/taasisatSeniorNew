"""
Django admin registration for Kernel models.

All kernel models are registered here for administrative access.
Admin is available at /admin/ for platform staff.
"""

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import Permission, Person, Role, RoleAssignment, Tenant, UserAccount


class UserAccountCreationForm(forms.ModelForm):
    """Add-user form bound to UserAccount. Django's built-in UserCreationForm
    has Meta.model hardcoded to auth.User (not get_user_model()), which
    breaks entirely for a swapped AUTH_USER_MODEL — this replaces it."""

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model = UserAccount
        fields = ("email", "phone", "person", "tenant", "is_staff")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserAccountChangeForm(forms.ModelForm):
    """Change-user form bound to UserAccount, mirroring Django's UserChangeForm
    (read-only password hash display) but pointed at the right model."""

    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text="Raw passwords are not stored, so there is no way to see this "
        'user\'s password, but you can change the password using <a href="../password/">this form</a>.',
    )

    class Meta:
        model = UserAccount
        fields = "__all__"

    def clean_password(self):
        return self.initial.get("password")


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
    form = UserAccountChangeForm
    add_form = UserAccountCreationForm
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
