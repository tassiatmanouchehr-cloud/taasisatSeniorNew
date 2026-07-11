"""
Shared role catalog — Epic 05 (Permission-Key Registry & Authorization
Hardening).

The repository had two independent, uncoordinated role-seeding commands
before this Epic: apps.kernel.management.commands.seed_tenant's
hyphenated DEFAULT_ROLES (seeds a "dev"-slug bootstrap tenant + superuser)
and apps.accounts.management.commands.seed_auth_roles's underscored ROLES
(seeds the real default "salmandyar" tenant
apps.kernel.services.tenant_service.TenantService actually resolves at
runtime). These are NOT the same taxonomy with cosmetic naming
differences — they cover overlapping but genuinely distinct role sets
(seed_tenant's is the broader "Correction Package Canonical Actor
Glossary"; seed_auth_roles's is the narrower set Epic 02-04 actually
enforce against). Force-merging them into one renamed taxonomy would mean
renaming live database Role rows and every RoleAssignment that references
them — exactly the "no destructive rename without a safe reconciliation
strategy" the System Architect's Epic 05 scope prohibits.

This module is the reconciliation this Epic DOES make: both commands'
role definitions now live here, in one place, as RoleDefinition entries —
so the full taxonomy is visible together, permission keys are validated
against the canonical registry, and any FUTURE slug divergence is caught
by KNOWN_SLUG_ALIASES / a guardrail test, rather than silently drifting
further. No existing slug is renamed here.

Located in apps.kernel (not apps.accounts): apps.kernel.management
.commands.seed_tenant lives in apps.kernel, which must never import a
higher-layer app (kernel sits at the root of the dependency graph — see
docs/architecture/dependency-graph.md). Permission keys are therefore
sourced from apps.kernel.permissions.keys directly (the canonical
registry, itself kernel-owned) rather than from apps.accounts
.permission_keys (a re-export facade one layer up) — both resolve to the
identical string values, this only matters for which direction the import
arrow points.

KNOWN_SLUG_ALIASES documents the one clear-cut case where both catalogs
almost certainly mean the same real-world role but spell it differently
("platform-owner" vs "platform_owner") — recorded as a known, deliberate,
not-yet-resolved divergence (see technical-debt-register.md), not hidden
and not auto-merged. Deciding which slug is canonical, and performing the
actual database-safe rename/merge, is a future, dedicated migration this
Epic does not attempt.
"""

from dataclasses import dataclass, field

from apps.kernel.permissions.keys import (
    ADMIN_FINANCE_READ,
    ADMIN_ORDERS_READ,
    ADMIN_PORTAL_ACCESS,
    ADMIN_SUPPLIERS_READ,
    ADMIN_SYSTEM_READ,
    ADMIN_TENANTS_READ,
    BOOKING_ASSIGNMENT_ASSIGN,
    ORGANIZATION_MEMBERSHIP_APPROVE,
    ORGANIZATION_MEMBERSHIP_SUSPEND,
    ORGANIZATION_PROFILE_UPDATE,
)


@dataclass(frozen=True)
class RoleDefinition:
    slug: str
    name: str
    description: str = ""
    is_system: bool = True
    permissions: tuple[str, ...] = field(default_factory=tuple)


# --- Roles consumed by apps.accounts.management.commands.seed_auth_roles ---
# (the real default tenant's role catalog)

ORGANIZATION_ADMIN_ROLE_SLUG = "organization_admin"
ORGANIZATION_ADMIN_ROLE_NAME = "مدیر سازمان"
ORGANIZATION_ADMIN_PERMISSIONS: tuple[str, ...] = (
    BOOKING_ASSIGNMENT_ASSIGN,
    ORGANIZATION_MEMBERSHIP_APPROVE,
    ORGANIZATION_MEMBERSHIP_SUSPEND,
    ORGANIZATION_PROFILE_UPDATE,
)

DEFAULT_TENANT_ROLES: tuple[RoleDefinition, ...] = (
    RoleDefinition(slug="platform_owner", name="مالک پلتفرم"),
    RoleDefinition(slug="platform_admin", name="مدیر پلتفرم"),
    RoleDefinition(slug="platform_operator", name="اپراتور پلتفرم"),
    RoleDefinition(slug="platform_support", name="پشتیبانی پلتفرم"),
    RoleDefinition(slug="platform_accounting", name="حسابداری پلتفرم"),
    RoleDefinition(slug="platform_security", name="امنیت پلتفرم"),
    RoleDefinition(slug="platform_it", name="فناوری اطلاعات پلتفرم"),
    RoleDefinition(slug="customer", name="مشتری / خانواده"),
    RoleDefinition(slug="independent_caregiver", name="مراقب مستقل"),
    RoleDefinition(slug="organization_caregiver", name="مراقب سازمانی"),
    RoleDefinition(
        slug=ORGANIZATION_ADMIN_ROLE_SLUG,
        name=ORGANIZATION_ADMIN_ROLE_NAME,
        description="Epic 04/05: carries the organization-isolation permission set.",
        permissions=ORGANIZATION_ADMIN_PERMISSIONS,
    ),
    RoleDefinition(slug="organization_operator", name="اپراتور سازمان"),
)

# --- Roles consumed by apps.kernel.management.commands.seed_tenant ---------
# (the dev-bootstrap tenant's role catalog — the broader Canonical Actor
# Glossary taxonomy)

ADMIN_PORTAL_PERMISSIONS: tuple[str, ...] = (
    ADMIN_PORTAL_ACCESS,
    ADMIN_TENANTS_READ,
    ADMIN_SUPPLIERS_READ,
    ADMIN_ORDERS_READ,
    ADMIN_FINANCE_READ,
    ADMIN_SYSTEM_READ,
)

DEV_BOOTSTRAP_ROLES: tuple[RoleDefinition, ...] = (
    RoleDefinition(
        slug="platform-owner",
        name="Platform Owner",
        description="Full platform access. Super-admin.",
        permissions=ADMIN_PORTAL_PERMISSIONS,
    ),
    RoleDefinition(
        slug="platform-team",
        name="Platform Team Member",
        description="Internal platform staff with delegated permissions.",
    ),
    RoleDefinition(
        slug="organization-owner", name="Organization Owner", description="Full access within own organization."
    ),
    RoleDefinition(
        slug="organization-staff",
        name="Organization Staff",
        description="Staff operating inside an organization with scoped permissions.",
    ),
    RoleDefinition(
        slug="organization-operator",
        name="Organization Operator",
        description="Dispatchers and coordinators within an organization.",
    ),
    RoleDefinition(
        slug="independent-provider",
        name="Independent Provider",
        description="Provider acting without organization affiliation.",
    ),
    RoleDefinition(
        slug="organization-provider",
        name="Organization Provider",
        description="Provider affiliated with an organization.",
    ),
    RoleDefinition(slug="customer", name="Customer", description="Person or entity requesting/buying a service."),
    RoleDefinition(
        slug="customer-delegate", name="Customer Delegate", description="Person acting on behalf of a customer account."
    ),
    RoleDefinition(
        slug="trusted-person",
        name="Trusted Person",
        description="Order-scoped person with limited, temporary visibility.",
    ),
    RoleDefinition(slug="support-user", name="Support User", description="Customer support staff."),
    RoleDefinition(slug="finance-user", name="Finance User", description="Financial operations staff."),
    RoleDefinition(slug="compliance-user", name="Compliance User", description="Compliance and governance staff."),
    RoleDefinition(
        slug="read-only-auditor", name="Read-Only Auditor", description="Audit access with no write permissions."
    ),
)

# Known, deliberate, NOT-YET-RESOLVED slug divergence — see module
# docstring. {dev_bootstrap_slug: default_tenant_slug}. Informational only;
# nothing in this codebase currently acts on this mapping.
KNOWN_SLUG_ALIASES: dict[str, str] = {
    "platform-owner": "platform_owner",
}


def all_role_definitions() -> tuple[RoleDefinition, ...]:
    """Every role definition across both catalogs — used by validation
    tooling (reconcile_role_permissions, guardrail tests) that needs to
    see the whole taxonomy at once."""
    return DEFAULT_TENANT_ROLES + DEV_BOOTSTRAP_ROLES
