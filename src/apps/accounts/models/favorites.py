"""
Favorite — Phase 4 Sprint 4.1 (Customer Favorites and Saved Providers).

A customer's own saved-supplier list — a normalized child table of the
existing `CustomerProfile` aggregate, following the exact shape
`CaregiverSkill`/`CaregiverGalleryItem`
(`apps/accounts/models/professional_profile.py`, `gallery.py`) already
established for owner-owned list-type child records in this app: plain
`models.Model`, UUID PK, FK with `related_name`, no `TenantAwareModel`
base — tenant is derived transitively via `customer_profile.user.tenant`,
never duplicated onto this row (see the Sprint 4.1 ADR in
`traceability/ARCHITECTURE_DECISION_LOG.md` for why this differs from
`apps.reviews.Review`'s own `tenant`-FK-plus-`person_id` shape: a
favorite is customer-owned preference data, structurally identical to
`ElderProfile`/`CaregiverSkill`, not a cross-module business-event record
like a review).

`supplier` targets `kernel.ServiceSupplier` only — never
`CaregiverProfile`/`OrganizationProfile` directly, the same unification
principle every other business module in this repository already follows
(`apps.kernel.tests.test_architecture_guardrails
.ServiceSupplierProfileCouplingTest`). This is what makes one model work
for both caregiver and organization favorites without a discriminated
subclass.

`on_delete=models.CASCADE` on both FKs, matching the dominant repository
precedent for FK-to-`ServiceSupplier` (`apps.availability`,
`apps.booking`, `apps.matching`, `apps.orders.OrderOffer`,
`apps.pricing` all use `CASCADE`) rather than `apps.reviews.Review`'s own
`PROTECT` (a review is a permanent historical/reputation record; a
favorite is a pure UI convenience toggle with no independent meaning once
its customer or supplier is gone — no historical-integrity concern
applies, confirmed by `ServiceSupplier` never being hard-deleted in any
production code path, only soft-transitioned via `SupplierStatus`).

Deletion is a hard delete — no soft-delete/archive field, matching this
app's own established convention (`VerificationDocument`, `CaregiverSkill`,
`CaregiverExperience`, `CaregiverGalleryItem` all hard-delete). A
favorite carries no history/audit value the way an `OrganizationMembership`
period does — unfavoriting and re-favoriting the same supplier is simply
a second `create()`, never a reactivation concern.
"""

import uuid

from django.db import models


class Favorite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_profile = models.ForeignKey(
        "accounts.CustomerProfile",
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    supplier = models.ForeignKey(
        "kernel.ServiceSupplier",
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_favorite"
        constraints = [
            models.UniqueConstraint(fields=["customer_profile", "supplier"], name="uq_customer_favorite_supplier"),
        ]
        indexes = [
            models.Index(fields=["customer_profile", "-created_at"], name="idx_favorite_customer_created"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer_profile_id}: favorite {self.supplier_id}"
