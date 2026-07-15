"""ActivationEligibilityService — Phase 1.2 (Verification Completion and
Activation Rules), corrected in the Phase 1.3 remediation (PR #5).

A pure, read-only query: "is this caregiver's/organization's profile
allowed to be activated right now, and if not, why." No side effects —
it does not activate, publish, or change anything. Since Phase 1.3,
`ProfileActivationService` is the caller that wires this into a real
DRAFT -> ACTIVE transition.

This is deliberately upstream of, and distinct from,
`apps.public_site.services.common.is_publicly_visible()` — that function
answers "should this ServiceSupplier row appear in marketplace listings
right now" (a kernel.ServiceSupplier / OrganizationMembership concern,
already implemented, unrelated to document verification). This service
answers a narrower, profile-level question: does the caregiver/
organization itself meet the platform's activation bar. The two may be
composed by a future caller; this task does not wire them together
(marketplace visibility is explicitly out of this task's scope).

Root defect fixed in the Phase 1.3 remediation: this service used to
require `status == ACTIVE` as an eligibility precondition, which is
circular once registration correctly starts a profile in DRAFT (a DRAFT
profile could never become "eligible," so it could never be activated).
Eligibility must instead distinguish *current activation state*
(`profile.status`, owned and mutated only by `ProfileActivationService`)
from *eligibility to become active* (this service). Eligibility requires
ALL of:
  - the profile's own `status` is not a blocking status — SUSPENDED or
    ARCHIVED. DRAFT and ACTIVE are both non-blocking: DRAFT is the normal
    pre-activation state a fresh registration starts in, and an
    already-ACTIVE profile remains evaluable (e.g. for display purposes,
    or so `ProfileActivationService`'s idempotent repeat-activation path
    can still reason about eligibility if it ever needs to).
  - the underlying UserAccount is active
  - the base profile is complete (100% — see MINIMUM_PROFILE_COMPLETION_PERCENT)
  - the rolled-up verification_status is VERIFIED (Part B) — this already
    folds in "no required document is pending/rejected/needing correction
    and no required document has expired"; expiry is not a separate check
    here because ProfileVerificationRollupService already excludes an
    expired VERIFIED document from the "approved" count
"""

from dataclasses import dataclass

from ..models.profiles import CaregiverProfile, OrganizationProfile, ProfileStatus, VerificationStatus
from .profiles import calculate_caregiver_profile_completion, calculate_organization_profile_completion
from .verification_rollup_service import ProfileVerificationRollupService, VerificationRollupResult

MINIMUM_PROFILE_COMPLETION_PERCENT = 100
"""The smallest explicit definition of "complete" available without
guessing a partial threshold no product evidence supports: every base
field present."""

BLOCKING_PROFILE_STATUSES = (ProfileStatus.SUSPENDED, ProfileStatus.ARCHIVED)
"""Statuses that block eligibility outright, regardless of completion or
verification. DRAFT and ACTIVE are deliberately excluded — see the module
docstring's "Root defect fixed" note."""


@dataclass(frozen=True)
class ActivationEligibilityResult:
    eligible: bool
    reasons: tuple[str, ...]
    verification: VerificationRollupResult


class ActivationEligibilityService:
    @classmethod
    def evaluate(cls, profile) -> ActivationEligibilityResult:
        if isinstance(profile, CaregiverProfile):
            return cls.evaluate_caregiver(profile)
        if isinstance(profile, OrganizationProfile):
            return cls.evaluate_organization(profile)
        raise TypeError(f"Unsupported profile type for activation eligibility: {type(profile)!r}")

    @classmethod
    def evaluate_caregiver(cls, caregiver: CaregiverProfile) -> ActivationEligibilityResult:
        reasons = []
        if caregiver.status in BLOCKING_PROFILE_STATUSES:
            reasons.append(f"profile_status_blocked:{caregiver.status}")
        if not caregiver.user.is_active:
            reasons.append("user_account_inactive")

        completion = calculate_caregiver_profile_completion(caregiver)
        if completion < MINIMUM_PROFILE_COMPLETION_PERCENT:
            reasons.append(f"profile_incomplete:{completion}percent")

        verification = ProfileVerificationRollupService.evaluate_caregiver(caregiver)
        cls._append_verification_reasons(reasons, verification)

        return ActivationEligibilityResult(eligible=not reasons, reasons=tuple(reasons), verification=verification)

    @classmethod
    def evaluate_organization(cls, organization: OrganizationProfile) -> ActivationEligibilityResult:
        reasons = []
        if organization.status in BLOCKING_PROFILE_STATUSES:
            reasons.append(f"profile_status_blocked:{organization.status}")
        if not organization.admin_user.is_active:
            reasons.append("user_account_inactive")

        completion = calculate_organization_profile_completion(organization)
        if completion < MINIMUM_PROFILE_COMPLETION_PERCENT:
            reasons.append(f"profile_incomplete:{completion}percent")

        verification = ProfileVerificationRollupService.evaluate_organization(organization)
        cls._append_verification_reasons(reasons, verification)

        return ActivationEligibilityResult(eligible=not reasons, reasons=tuple(reasons), verification=verification)

    @staticmethod
    def _append_verification_reasons(reasons: list, verification: VerificationRollupResult) -> None:
        if verification.verification_status != VerificationStatus.VERIFIED:
            reasons.append(f"documents_not_verified:{verification.verification_status}")
        if verification.needs_correction:
            reasons.append("documents_need_correction")
