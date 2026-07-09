"""
RBAC permission_key taxonomy for the admin portal — Module 19.

Follows the same convention as apps.api.permission_keys
(documented in docs/architecture/rbac-permissions.md): `<domain>.<action>`,
lowercase, dot-separated. No permission_key registry exists anywhere in
the platform (Role.permissions is a freeform JSON string list — see
apps.kernel.models.rbac); these constants exist so keys aren't scattered
as magic strings across view modules. Roles must be granted these keys
explicitly — nothing here auto-grants access to "platform owner" or any
other role.
"""

PORTAL_ACCESS = "admin.portal.access"
TENANTS_READ = "admin.tenants.read"
SUPPLIERS_READ = "admin.suppliers.read"
ORDERS_READ = "admin.orders.read"
FINANCE_READ = "admin.finance.read"
SYSTEM_READ = "admin.system.read"
