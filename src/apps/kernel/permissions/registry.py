"""
Canonical permission-key registry — Epic 05 (Permission-Key Registry &
Authorization Hardening).

This is NOT a policy engine and does not replace RBAC. `PermissionService`
(apps.kernel.services.permission_service) remains the sole evaluator of
`Role`/`RoleAssignment` for an authorization decision; this registry only
answers "does this key exist, and what does it mean" — evaluation is
unchanged.

Located in apps.kernel (the root of the dependency graph — nothing kernel
imports back) so every business app can import it without creating a
cycle. Deliberately a plain Python module, not a database table: see
apps.kernel.models.rbac.Permission's own docstring and
docs/adr/ADR-010_CANONICAL_PERMISSION_REGISTRY.md for why the existing,
still-dormant `Permission` model was NOT chosen as the source of truth —
in short, nothing at runtime reads `Permission.objects`
(`PermissionService` evaluates `Role.permissions`, a freeform JSON list),
so populating it would create a second thing to keep in sync with zero
runtime consumer to justify the ongoing cost.

Existing per-app `permission_keys.py` modules (`apps.api`,
`apps.admin_portal`, `apps.accounts`) are re-export facades over this
registry, not parallel sources of truth — see each of their own files.
"""

import re
from dataclasses import dataclass

_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,2}$")


class PermissionRegistryError(Exception):
    pass


@dataclass(frozen=True)
class PermissionKey:
    """Lightweight metadata for one permission_key. Immutable — a key's
    metadata is fixed at registration time (module import), never mutated
    at runtime."""

    key: str
    domain: str
    resource: str
    action: str
    description: str
    organization_scope: bool = False
    """True if this key is meaningfully checked with scope={"scope_type":
    "organization", ...} — informational only; PermissionService itself
    does not consult this field (see docs/architecture/rbac-permissions.md
    for the current, unchanged scope-evaluation rules)."""
    platform_scope: bool = False
    """True if this key is a platform-wide capability never expected to
    carry an organization/branch scope."""
    internal_only: bool = False
    """True if this key is only ever checked from internal/system call
    sites (actor=None) — informational, does not change enforcement."""


class PermissionRegistry:
    """Central, in-memory registry of every real permission_key in the
    platform. One entry per key that actually has a PermissionService
    enforcement call site — see each key's own registration comment for
    that call site."""

    _entries: dict[str, PermissionKey] = {}

    @classmethod
    def register(cls, permission: PermissionKey) -> PermissionKey:
        if not _KEY_PATTERN.match(permission.key):
            raise PermissionRegistryError(
                f"Malformed permission key {permission.key!r} — must be "
                "lowercase, dot-separated, 2 or 3 segments "
                "(<domain>.<action> or <domain>.<resource>.<action>).",
            )
        if permission.key in cls._entries:
            raise PermissionRegistryError(f"Duplicate permission key: {permission.key!r}")
        cls._entries[permission.key] = permission
        return permission

    @classmethod
    def get(cls, key: str) -> PermissionKey | None:
        return cls._entries.get(key)

    @classmethod
    def exists(cls, key: str) -> bool:
        return key in cls._entries

    @classmethod
    def all(cls) -> tuple[PermissionKey, ...]:
        return tuple(cls._entries.values())

    @classmethod
    def keys(cls) -> tuple[str, ...]:
        return tuple(cls._entries.keys())

    @classmethod
    def by_domain(cls, domain: str) -> tuple[PermissionKey, ...]:
        return tuple(p for p in cls._entries.values() if p.domain == domain)


def register(
    key: str,
    *,
    domain: str,
    resource: str,
    action: str,
    description: str,
    organization_scope: bool = False,
    platform_scope: bool = False,
    internal_only: bool = False,
) -> str:
    """Convenience wrapper: register a key and return its string value, so
    call sites can do `FOO = register("domain.resource.action", ...)`
    directly at module scope."""
    PermissionRegistry.register(
        PermissionKey(
            key=key,
            domain=domain,
            resource=resource,
            action=action,
            description=description,
            organization_scope=organization_scope,
            platform_scope=platform_scope,
            internal_only=internal_only,
        )
    )
    return key
