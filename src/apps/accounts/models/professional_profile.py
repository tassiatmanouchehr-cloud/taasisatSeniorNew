"""
CaregiverSkill / CaregiverExperience — Phase 2.1 (Caregiver Professional
Profile Foundation).

Two small, normalized, caregiver-owned child tables — the smallest
correct model this phase's scope calls for. Neither introduces a second
caregiver identity or a parallel profile: both are plain FKs to the
existing `CaregiverProfile` aggregate, following the exact shape
`VerificationDocument` (`apps/accounts/models/media.py`) already
established for caregiver-owned child records in this app (plain
`models.Model`, UUID PK, FK with `related_name`, no `TenantAwareModel`
base — tenant is derived transitively via `caregiver.user.tenant`, never
duplicated onto the child row).

No skill catalog/taxonomy table was added — no repository evidence
supports one, and Phase 2.1's own governance calls for "the smallest
normalized model consistent with repository conventions," not a new
catalog concept. `unique_together` on (caregiver, name) is the database
backstop for exact-duplicate names; case-insensitive duplicate detection
is a service-layer concern (`CaregiverSkillService`), not a DB constraint,
for the same reason `RequiredDocumentPolicy` keeps its own normalization
at the service layer rather than the schema layer.

Neither model implies verification — a caregiver's own claim of a skill
or a role is never treated as platform-verified. Only `VerificationDocument`
(reviewed by `VerificationReviewService`) carries that meaning.
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models


class CaregiverSkill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    caregiver = models.ForeignKey(
        "accounts.CaregiverProfile",
        on_delete=models.CASCADE,
        related_name="skills",
    )
    name = models.CharField(max_length=100)
    display_order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_caregiver_skill"
        constraints = [
            models.UniqueConstraint(fields=["caregiver", "name"], name="uq_caregiver_skill_name"),
        ]
        ordering = ["display_order", "created_at"]

    def __str__(self):
        return f"{self.caregiver_id}: {self.name}"


class CaregiverExperience(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    caregiver = models.ForeignKey(
        "accounts.CaregiverProfile",
        on_delete=models.CASCADE,
        related_name="experiences",
    )
    title = models.CharField(max_length=150)
    organization_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, max_length=2000)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_caregiver_experience"
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__isnull=True) | models.Q(end_date__gte=models.F("start_date")),
                name="ck_caregiver_experience_end_after_start",
            ),
        ]
        ordering = ["-is_current", "-start_date"]

    def __str__(self):
        return f"{self.caregiver_id}: {self.title}"

    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")
