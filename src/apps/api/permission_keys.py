"""
RBAC permission_key taxonomy — Module 17A/17B, documented in
docs/architecture/rbac-permissions.md.

No permission_key registry exists anywhere in the platform yet
(Role.permissions is a freeform JSON string list — see
apps.kernel.models.rbac). These constants establish a first naming
convention (`<domain>.<action>`) for API-exposed capabilities so keys
aren't scattered as magic strings across view modules. Roles must be
granted these keys explicitly (see apps.kernel.tests.rbac_helpers.
grant_permissions) — nothing here auto-grants access.
"""

REPORTING_READ = "reporting.read"
DISCOVERY_SUPPLIERS_READ = "discovery.suppliers.read"
PRICING_QUOTES_CREATE = "pricing.quotes.create"
REVIEWS_SUBMIT = "reviews.submit"
REVIEWS_READ = "reviews.read"
WALLET_READ = "wallet.read"
PAYMENTS_INTENTS_CREATE = "payments.intents.create"
PAYMENTS_ATTEMPTS_CREATE = "payments.attempts.create"
