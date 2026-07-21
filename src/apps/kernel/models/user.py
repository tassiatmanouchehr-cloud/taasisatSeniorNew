"""
Person and UserAccount models.

Person: Stable natural-person identity. Never duplicated. Permanent.
UserAccount: Authentication account bound to a Person. Temporal.

A Person may have multiple UserAccounts (phone-based, email-based, OAuth).
A UserAccount is used for login; a Person is the stable identity across all roles.

References:
- ADR-001.01 (Person is separate from UserAccount)
- ADR-001.02 (User is not Provider)
- Phase 0.5 Deliverable 2 (Person / Identity Model)
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class PersonStatus(models.TextChoices):
    """Person lifecycle states."""

    ACTIVE = "active", "Active"
    DEACTIVATED = "deactivated", "Deactivated"


class Person(models.Model):
    """
    Stable natural-person identity — never duplicated.

    Person.id is permanent. A Person is never deleted, only deactivated.
    Roles, memberships, and profiles are attached to Person but are temporal.
    Other modules reference Person.id for actor tracking.

    Per Domain Model Freeze: Person is a Kernel entity owned by Module 25.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="persons",
    )
    full_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=PersonStatus.choices,
        default=PersonStatus.ACTIVE,
        db_index=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = 'kernel"."person'
        verbose_name = "Person"
        verbose_name_plural = "Persons"

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.version += 1
        super().save(*args, **kwargs)


class UserAccountManager(BaseUserManager):
    """Custom manager for UserAccount — UUID-based, no username."""

    def create_user(self, email=None, phone=None, password=None, **extra_fields):
        """Create a regular user account."""
        if not email and not phone:
            raise ValueError("UserAccount must have either email or phone")
        if email:
            email = self.normalize_email(email)
        user = self.model(email=email or None, phone=phone or "", **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, phone=None, password=None, **extra_fields):
        """Create a superuser account (for Django admin access)."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True")
        return self.create_user(email=email, phone=phone, password=password, **extra_fields)


class UserAccount(AbstractBaseUser, PermissionsMixin):
    """
    Authentication account bound to a Person.

    UserAccount is for login only. It does NOT contain profile data,
    provider information, or business context. Those belong to Module 08 profiles.

    A Person may have multiple UserAccounts (e.g., one per login method).
    AUTH_USER_MODEL points here for Django's auth system.

    Per ADR-001.01: Person is separate from UserAccount.
    Per ADR-001.02: User is not Provider.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="accounts",
        null=True,
        blank=True,
        help_text="The Person this account belongs to. Null for initial superuser only.",
    )
    tenant = models.ForeignKey(
        "kernel.Tenant",
        on_delete=models.PROTECT,
        related_name="user_accounts",
        null=True,
        blank=True,
        help_text="Tenant this account belongs to. Null for platform superuser only.",
    )
    email = models.EmailField(max_length=255, null=True, blank=True, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether this user can access the admin site.",
    )
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserAccountManager()

    # Human-friendly login identifier — email, not the UUID primary key.
    # null=True (not "") lets phone-only accounts share a blank email
    # without violating uniqueness (Postgres allows multiple NULLs under a
    # unique constraint). The existing phone-based OTP login flow
    # (apps.accounts.views) never goes through Django's authenticate(), so
    # it is unaffected by this — only /admin/ login and createsuperuser use
    # USERNAME_FIELD.
    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'kernel"."user_account'
        verbose_name = "User Account"
        verbose_name_plural = "User Accounts"

    def __str__(self):
        return self.email or self.phone or str(self.id)
