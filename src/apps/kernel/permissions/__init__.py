"""Canonical permission-key registry — see .registry and .keys."""

from .registry import PermissionKey, PermissionRegistry, PermissionRegistryError, register

__all__ = ["PermissionKey", "PermissionRegistry", "PermissionRegistryError", "register"]
