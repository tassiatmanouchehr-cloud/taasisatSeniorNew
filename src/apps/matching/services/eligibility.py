"""
Eligibility Service — Module 02 Matching Engine.

Evaluates whether a single ServiceSupplier is eligible to be a candidate
for a given Order. Pure evaluation: no persistence, no side effects.

Per ADR-02-07 (Explainable Eligibility): every result carries a structured
code plus a reason payload, never free text only.
"""

from dataclasses import dataclass, field
from typing import Any

from apps.kernel.models.supplier import AvailabilityStatus, ServiceSupplier, SupplierStatus
from apps.kernel.services.supplier_resolver import SupplierResolver

from ..models import EligibilityCode
from .configuration import MatchingConfiguration

# Availability states that make a supplier ineligible outright.
INELIGIBLE_AVAILABILITY = {AvailabilityStatus.OFFLINE, AvailabilityStatus.ON_LEAVE}

# Ordinal ranking of verification levels, lowest to highest.
VERIFICATION_LEVEL_ORDER = {
    "unverified": 0,
    "basic": 1,
    "advanced": 2,
    "premium": 3,
}


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    code: str
    reason: dict[str, Any] = field(default_factory=dict)


class EligibilityService:
    """Evaluates ServiceSupplier eligibility for a given Order."""

    @classmethod
    def evaluate(cls, *, order, supplier: ServiceSupplier) -> EligibilityResult:
        if supplier.tenant_id != order.tenant_id:
            return EligibilityResult(
                eligible=False,
                code=EligibilityCode.WRONG_TENANT,
                reason={
                    "supplier_tenant_id": str(supplier.tenant_id),
                    "order_tenant_id": str(order.tenant_id),
                },
            )

        if supplier.status != SupplierStatus.ACTIVE:
            return EligibilityResult(
                eligible=False,
                code=EligibilityCode.SUPPLIER_NOT_ACTIVE,
                reason={"status": supplier.status},
            )

        if supplier.availability_status in INELIGIBLE_AVAILABILITY:
            return EligibilityResult(
                eligible=False,
                code=EligibilityCode.SUPPLIER_UNAVAILABLE,
                reason={"availability_status": supplier.availability_status},
            )

        if not SupplierResolver.is_supplier_type_allowed(
            tenant_id=order.tenant_id,
            supplier_type=supplier.supplier_type,
        ):
            return EligibilityResult(
                eligible=False,
                code=EligibilityCode.SUPPLIER_TYPE_NOT_ALLOWED,
                reason={"supplier_type": supplier.supplier_type},
            )

        category_id = str(order.service_category_id)
        supported_categories = [str(c) for c in (supplier.service_categories or [])]
        if category_id not in supported_categories:
            return EligibilityResult(
                eligible=False,
                code=EligibilityCode.CATEGORY_NOT_SUPPORTED,
                reason={
                    "service_category_id": category_id,
                    "supplier_service_categories": supported_categories,
                },
            )

        min_level = MatchingConfiguration.get_minimum_verification_level(tenant_id=order.tenant_id)
        if min_level and not cls._meets_verification_level(supplier.verification_level, min_level):
            return EligibilityResult(
                eligible=False,
                code=EligibilityCode.BELOW_VERIFICATION_THRESHOLD,
                reason={
                    "verification_level": supplier.verification_level,
                    "required_verification_level": min_level,
                },
            )

        return EligibilityResult(eligible=True, code=EligibilityCode.ELIGIBLE, reason={})

    @staticmethod
    def _meets_verification_level(actual: str, required: str) -> bool:
        return VERIFICATION_LEVEL_ORDER.get(actual, 0) >= VERIFICATION_LEVEL_ORDER.get(required, 0)
