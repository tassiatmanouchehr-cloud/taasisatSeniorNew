"""ProfileCompletionService — Phase 1.3 (Profile Activation and Completion).

Single source of truth for the labeled base-profile-field checklist
behind `apps.accounts.services.profiles.calculate_caregiver_profile_completion()`/
`calculate_organization_profile_completion()` (Phase 1.2) — both now
delegate their percentage to this module instead of maintaining a
second, duplicate field list. Adds the completed/missing breakdown those
bare-int functions never exposed, which `ActivationEligibilityService`'s
structured reasons and the owner-facing "what's missing" UI both need.

Base-profile-field completeness only — document verification remains a
separate concern (`ProfileVerificationRollupService`), not conflated
here, exactly matching the design decision Phase 1.2 already recorded on
`calculate_organization_profile_completion()`'s own docstring.

Deterministic and idempotent by construction: a pure function of the
profile's current field values, no randomness, no hidden state, safe to
call any number of times.
"""

from dataclasses import dataclass

from ..models.profiles import CaregiverProfile, OrganizationProfile

CAREGIVER_COMPLETION_FIELDS: tuple[tuple[str, str], ...] = (
    ("display_name", "نام نمایشی"),
    ("phone", "شماره تماس"),
    ("city", "شهر"),
    ("specialty", "تخصص"),
    ("bio", "بیوگرافی"),
    ("years_experience", "سابقه کار"),
    ("service_radius_km", "شعاع خدمت‌رسانی"),
)
"""Mirrors the exact field set `calculate_caregiver_profile_completion()`
already checked pre-Phase-1.3 — no fields added or removed, only labeled."""

ORGANIZATION_COMPLETION_FIELDS: tuple[tuple[str, str], ...] = (
    ("name", "نام سازمان"),
    ("city", "شهر"),
    ("phone", "شماره تماس"),
    ("address", "آدرس"),
    ("description", "توضیحات"),
    ("company_type", "نوع فعالیت"),
)
"""Mirrors the exact field set `calculate_organization_profile_completion()`
(Phase 1.2) already checked — no fields added or removed, only labeled."""


@dataclass(frozen=True)
class ProfileCompletionResult:
    percent: int
    completed: tuple[str, ...]
    missing: tuple[str, ...]


class ProfileCompletionService:
    @classmethod
    def evaluate_caregiver(cls, profile: CaregiverProfile) -> ProfileCompletionResult:
        return cls._evaluate(profile, CAREGIVER_COMPLETION_FIELDS)

    @classmethod
    def evaluate_organization(cls, profile: OrganizationProfile) -> ProfileCompletionResult:
        return cls._evaluate(profile, ORGANIZATION_COMPLETION_FIELDS)

    @staticmethod
    def _evaluate(profile, field_spec: tuple[tuple[str, str], ...]) -> ProfileCompletionResult:
        """`value not in (None, "")` is exactly equivalent to the field-by-
        field checks the pre-Phase-1.3 bare functions used (`bool(x)` for
        text fields — blank string is falsy; `x is not None` for the two
        optional integer fields, where a legitimate `0` must still count
        as filled — `0 not in (None, "")` is True, matching that original
        `is not None` check rather than a truthiness check that would
        wrongly treat 0 years of experience as "missing")."""
        completed, missing = [], []
        for field_name, label in field_spec:
            value = getattr(profile, field_name)
            if value not in (None, ""):
                completed.append(label)
            else:
                missing.append(label)
        percent = int((len(completed) / len(field_spec)) * 100) if field_spec else 100
        return ProfileCompletionResult(percent=percent, completed=tuple(completed), missing=tuple(missing))
