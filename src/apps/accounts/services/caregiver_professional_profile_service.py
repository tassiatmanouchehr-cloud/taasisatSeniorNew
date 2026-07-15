"""
CaregiverSkillService / CaregiverExperienceService — Phase 2.1 (Caregiver
Professional Profile Foundation).

Owner-authorized read-write for `CaregiverSkill`/`CaregiverExperience`,
mirroring the exact shape `apps.accounts.services.caregiver_profile_service
.CaregiverProfileUpdateService` already established for caregiver
self-service edits: no RBAC permission key (ownership, not a role, is the
authorization boundary — the caller already had to resolve their own
`CaregiverProfile` via `request.user.caregiver_profile` before reaching
here, exactly as the existing basic/professional-info edit views do), a
fixed, explicit, field-whitelisted API (never generic `update(**kwargs)`),
and every mutation re-verifies `record.caregiver_id == caregiver.id`
before touching a specific row — defense-in-depth against a caller
passing an id belonging to someone else's record.

No endorsements, rankings, or skill-verification workflow — a caregiver's
own skill/experience entries are never treated as platform-verified (see
this app's `professional_profile.py` model docstring).
"""

from django.db import IntegrityError, transaction

from ..models.professional_profile import CaregiverExperience, CaregiverSkill
from .errors import AccountsError

MAX_SKILL_NAME_LENGTH = 100
MAX_EXPERIENCE_TITLE_LENGTH = 150


class CaregiverSkillService:
    """Read-write: a caregiver's own skill list only."""

    @classmethod
    def list_skills(cls, caregiver):
        return CaregiverSkill.objects.filter(caregiver=caregiver)

    @classmethod
    @transaction.atomic
    def add_skill(cls, caregiver, *, name: str) -> CaregiverSkill:
        cleaned = (name or "").strip()
        if not cleaned:
            raise AccountsError("Skill name is required.")
        if len(cleaned) > MAX_SKILL_NAME_LENGTH:
            raise AccountsError(f"Skill name exceeds {MAX_SKILL_NAME_LENGTH} characters.")
        if CaregiverSkill.objects.filter(caregiver=caregiver, name__iexact=cleaned).exists():
            raise AccountsError("This skill has already been added.")

        try:
            with transaction.atomic():
                return CaregiverSkill.objects.create(caregiver=caregiver, name=cleaned)
        except IntegrityError:
            # The .exists() pre-check above is not itself race-proof — two
            # concurrent "add the same skill" submissions can both pass it
            # before either commits. uq_caregiver_skill_name is what
            # actually serializes them; this turns the resulting
            # IntegrityError into the same controlled domain error the
            # pre-check already raises for the common case.
            raise AccountsError("This skill has already been added.") from None

    @classmethod
    def remove_skill(cls, caregiver, *, skill_id) -> None:
        deleted, _ = CaregiverSkill.objects.filter(id=skill_id, caregiver=caregiver).delete()
        if not deleted:
            raise AccountsError("Skill not found.")


class CaregiverExperienceService:
    """Read-write: a caregiver's own experience entries only."""

    @classmethod
    def list_experiences(cls, caregiver):
        return CaregiverExperience.objects.filter(caregiver=caregiver)

    @classmethod
    def create(
        cls,
        caregiver,
        *,
        title: str,
        organization_name: str = "",
        description: str = "",
        start_date,
        end_date=None,
        is_current: bool = False,
    ) -> CaregiverExperience:
        cls._validate(title=title, start_date=start_date, end_date=end_date, is_current=is_current)
        return CaregiverExperience.objects.create(
            caregiver=caregiver,
            title=title.strip(),
            organization_name=(organization_name or "").strip(),
            description=(description or "").strip(),
            start_date=start_date,
            end_date=None if is_current else end_date,
            is_current=is_current,
        )

    @classmethod
    def update(
        cls,
        caregiver,
        *,
        experience_id,
        title: str,
        organization_name: str = "",
        description: str = "",
        start_date,
        end_date=None,
        is_current: bool = False,
    ) -> CaregiverExperience:
        cls._validate(title=title, start_date=start_date, end_date=end_date, is_current=is_current)
        try:
            experience = CaregiverExperience.objects.get(id=experience_id, caregiver=caregiver)
        except CaregiverExperience.DoesNotExist:
            raise AccountsError("Experience entry not found.") from None

        experience.title = title.strip()
        experience.organization_name = (organization_name or "").strip()
        experience.description = (description or "").strip()
        experience.start_date = start_date
        experience.end_date = None if is_current else end_date
        experience.is_current = is_current
        experience.save(
            update_fields=[
                "title", "organization_name", "description",
                "start_date", "end_date", "is_current", "updated_at",
            ],
        )
        return experience

    @classmethod
    def delete(cls, caregiver, *, experience_id) -> None:
        deleted, _ = CaregiverExperience.objects.filter(id=experience_id, caregiver=caregiver).delete()
        if not deleted:
            raise AccountsError("Experience entry not found.")

    @staticmethod
    def _validate(*, title, start_date, end_date, is_current) -> None:
        if not (title or "").strip():
            raise AccountsError("Title is required.")
        if len(title.strip()) > MAX_EXPERIENCE_TITLE_LENGTH:
            raise AccountsError(f"Title exceeds {MAX_EXPERIENCE_TITLE_LENGTH} characters.")
        if not start_date:
            raise AccountsError("Start date is required.")
        if not is_current and end_date and end_date < start_date:
            raise AccountsError("End date cannot be before start date.")
