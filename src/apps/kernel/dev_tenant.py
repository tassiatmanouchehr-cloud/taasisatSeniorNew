"""Single source of truth for this repository's local-development
walkthrough tenant slug.

FR-019 corrective review: the canonical public URL (/find-a-caregiver/)
must show `seed_product_walkthrough`'s realistic demo caregivers with no
`?tenant=` query parameter and no manual `.env` edit after copying
`.env.example`. That requires `apps.public_site.services.tenant_context
.resolve_public_tenant()` and `apps.kernel.management.commands
.seed_product_walkthrough` to agree on the exact same tenant slug — this
module is that single, literal agreement point, so the two can never
silently drift apart. Both import `CANONICAL_DEV_TENANT_SLUG` from here;
neither defines its own copy of the string.

Deliberately a plain, Django-app-independent module (no model imports,
no `django.apps` dependency) — this makes it safe to import from
`apps.public_site.services.tenant_context` at ordinary request-handling
time (long after the app registry is ready, no concern there) and,
just as importantly, keeps the door open for it to be imported from a
settings module in the future without ever risking an
AppRegistryNotReady failure, without actually requiring that today."""

CANONICAL_DEV_TENANT_SLUG = "demo-senior-platform"
