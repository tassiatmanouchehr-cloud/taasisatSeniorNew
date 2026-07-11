"""
CaregiverProfileUpdateService — Epic 06 Sprint 2 (Shared Portal UI Core,
Provider Profile, Organization Profile).

The one and only writer for the fields a caregiver is authorized to edit
on their own profile. Deliberately field-whitelisted: only
update_basic_info()/update_professional_info() exist, each touching an
explicit, fixed field set — there is no generic "update(**kwargs)"
method, so no caller (this Sprint's or any future one) can accidentally
mass-assign a field a caregiver should never control.

Neither method ever touches `verification_status`, `status`,
`provider_type`, `user`, `person`, or `phone` — verification remains
controlled exclusively by a future platform-admin workflow (not built
this Sprint), account status/type transitions remain controlled by their
own existing sanctioned services, and identity fields are not
self-editable at all.
"""

from apps.kernel.services.supplier_registry import SupplierRegistry

from .supplier_bridge import get_or_create_supplier_for_caregiver


class CaregiverProfileUpdateService:
    """Read-write: the caregiver's own editable profile fields."""

    @classmethod
    def update_basic_info(cls, caregiver, *, display_name: str, city: str):
        caregiver.display_name = (display_name or "").strip()
        caregiver.city = (city or "").strip()
        caregiver.save(update_fields=["display_name", "city", "updated_at"])

        # ServiceSupplier.display_name mirrors the profile's own — kept in
        # sync through the sanctioned bridge/registry, never written to
        # ServiceSupplier directly from this app.
        supplier = get_or_create_supplier_for_caregiver(caregiver)
        if supplier.display_name != caregiver.display_name:
            supplier.display_name = caregiver.display_name
            supplier.save(update_fields=["display_name", "updated_at", "version"])
        return caregiver

    @classmethod
    def update_professional_info(
        cls,
        caregiver,
        *,
        bio: str,
        specialty: str,
        years_experience: int | None,
        service_radius_km: int | None,
        service_category_ids: list[str] | None = None,
    ):
        caregiver.bio = (bio or "").strip()
        caregiver.specialty = (specialty or "").strip()
        caregiver.years_experience = years_experience
        caregiver.service_radius_km = service_radius_km
        caregiver.save(
            update_fields=["bio", "specialty", "years_experience", "service_radius_km", "updated_at"],
        )

        if service_category_ids is not None:
            supplier = get_or_create_supplier_for_caregiver(caregiver)
            SupplierRegistry.set_service_categories(supplier, service_category_ids=service_category_ids)

        return caregiver
