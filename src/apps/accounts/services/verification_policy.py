"""Required-document policy — Phase 1.2 (Verification Completion and
Activation Rules).

Defines which `VerificationDocument` types are MANDATORY vs OPTIONAL for
each profile type this repository actually supports document review for
(caregiver, organization). Tenant-overridable via the existing
`ConfigResolver`/`ConfigurationKey` infrastructure — mirrors every other
`*Configuration` wrapper in this codebase (e.g.
`apps.commission.services.configuration.CommissionConfiguration`); no new
configuration mechanism was introduced, and no `ConfigurationKey` row
needs to exist for the defaults below to apply (`ConfigResolver
.get_or_default()` falls back cleanly when unregistered — the same
zero-seeding behavior every existing gate already relies on).

Applicable-type universe: intentionally mirrors, at the correct
dependency layer, the exact partition
`apps.provider_portal.services.profile_service.PROVIDER_DOCUMENT_TYPES`
and `apps.organization_portal.services.profile_service
.ORGANIZATION_DOCUMENT_TYPES` already establish (5 caregiver-relevant +
4 organization-relevant = all 9 `DocumentType` members). `apps.accounts`
sits upstream of both portal apps and cannot import from them — this
restates the same, already-consistent fact at the correct layer rather
than creating a second, divergent one.

Required subset (the new decision this module actually makes): the
smallest defensible mandatory set per profile type for a senior-care
marketplace — IDENTITY (who they are) and BACKGROUND_CHECK (safety-
critical for anyone entering an elder's home) for caregivers;
REGISTRATION (legal existence) and OPERATING_LICENSE (licensed to
operate a care business) for organizations. Everything else in the
applicable set (QUALIFICATION/TRAINING_CERTIFICATE/LICENSE for
caregivers, INSURANCE/PROFESSIONAL_PERMIT for organizations) is optional
— it strengthens a profile but does not gate verification. This is a
product policy choice, not a derived fact, which is exactly why it is
tenant-overridable rather than hard-coded as an unconditional constant.

Per-service variation: NOT implemented. No repository infrastructure
ties `ServiceCategory`/`ServiceType` to document requirements —
inventing one here would be guessing a business rule with no evidence to
ground it.

Customer document verification: NOT implemented. `VerificationDocument`
has no customer-owner FK and `CustomerProfile` has no
`verification_status` field anywhere in this repository (confirmed
during Phase 1.1; unchanged here). Phone/OTP verification
(`apps.accounts.services.otp.OTPService`, already implemented and
required at registration) is the current-phase identity verification
mechanism for customers — see `quality/COMPLETION_BACKLOG.md` BG-016.

Expiry handling: a required document's DB `status` is never mutated by
expiry — expiry is a derived, point-in-time fact, exactly matching the
pattern `apps.provider_portal`/`apps.organization_portal`'s own
presentation services already use ("VERIFIED but `expiry_date` < today"
-> shown as "expired"). `is_effectively_expired()` below is that same
rule, reusable outside the portal layer for the verification roll-up
(Part B) and activation eligibility (Part D).

Rejection handling: a rejected required document blocks roll-up
(profile stays NOT VERIFIED) until the owner resubmits via
`DocumentService.resubmit()` (Part C), which resets it to PENDING — no
separate rejection-specific policy is needed beyond what the roll-up
state machine already expresses.

Expiring-soon (Sprint 2.3, Credentials/Skills/Experience/Highlights):
`is_expiring_soon()` is a sibling of `is_effectively_expired()` — same
derived, point-in-time-fact shape, no DB status mutation, no new field.
Owner-facing only (surfaced on the provider portal's own document status
row); never consulted by the public `PublicCredentialSelector`, which
already excludes anything `is_effectively_expired()` and has no
"expiring soon" concept of its own — a still-valid, still-verified
credential is shown publicly exactly as before, regardless of how soon
it expires.
"""

from apps.kernel.services.config_resolver import ConfigResolver

from ..models.media import DocumentStatus, DocumentType

CAREGIVER_APPLICABLE_DOCUMENT_TYPES = (
    DocumentType.IDENTITY,
    DocumentType.BACKGROUND_CHECK,
    DocumentType.QUALIFICATION,
    DocumentType.TRAINING_CERTIFICATE,
    DocumentType.LICENSE,
)

ORGANIZATION_APPLICABLE_DOCUMENT_TYPES = (
    DocumentType.REGISTRATION,
    DocumentType.OPERATING_LICENSE,
    DocumentType.INSURANCE,
    DocumentType.PROFESSIONAL_PERMIT,
)

CAREGIVER_REQUIRED_DOCUMENT_TYPES_KEY = "accounts.caregiver.required_document_types"
DEFAULT_CAREGIVER_REQUIRED_DOCUMENT_TYPES = (DocumentType.IDENTITY, DocumentType.BACKGROUND_CHECK)

ORGANIZATION_REQUIRED_DOCUMENT_TYPES_KEY = "accounts.organization.required_document_types"
DEFAULT_ORGANIZATION_REQUIRED_DOCUMENT_TYPES = (DocumentType.REGISTRATION, DocumentType.OPERATING_LICENSE)


class RequiredDocumentPolicy:
    @classmethod
    def required_caregiver_document_types(cls, *, tenant_id) -> tuple[str, ...]:
        value = ConfigResolver.get_or_default(
            CAREGIVER_REQUIRED_DOCUMENT_TYPES_KEY,
            tenant_id=tenant_id,
            default=list(DEFAULT_CAREGIVER_REQUIRED_DOCUMENT_TYPES),
        )
        return cls._sanitize(value, DEFAULT_CAREGIVER_REQUIRED_DOCUMENT_TYPES, CAREGIVER_APPLICABLE_DOCUMENT_TYPES)

    @classmethod
    def required_organization_document_types(cls, *, tenant_id) -> tuple[str, ...]:
        value = ConfigResolver.get_or_default(
            ORGANIZATION_REQUIRED_DOCUMENT_TYPES_KEY,
            tenant_id=tenant_id,
            default=list(DEFAULT_ORGANIZATION_REQUIRED_DOCUMENT_TYPES),
        )
        return cls._sanitize(
            value, DEFAULT_ORGANIZATION_REQUIRED_DOCUMENT_TYPES, ORGANIZATION_APPLICABLE_DOCUMENT_TYPES,
        )

    @staticmethod
    def _sanitize(value, default, applicable) -> tuple[str, ...]:
        """A tenant override that isn't a list, or that names a type not
        applicable to this profile kind, falls back to the code default
        rather than silently requiring a nonsensical document — an
        override can narrow within the applicable set, never invent
        outside it."""
        if not isinstance(value, (list, tuple)):
            return tuple(default)
        applicable_values = {str(t) for t in applicable}
        sanitized = tuple(v for v in value if v in applicable_values)
        return sanitized or tuple(default)

    @staticmethod
    def is_effectively_expired(document) -> bool:
        from django.utils import timezone

        return (
            document.status == DocumentStatus.VERIFIED
            and document.expiry_date is not None
            and document.expiry_date < timezone.now().date()
        )

    EXPIRING_SOON_WINDOW_DAYS = 30

    @classmethod
    def is_expiring_soon(cls, document) -> bool:
        """True only for a currently-valid VERIFIED document whose expiry
        falls within the next EXPIRING_SOON_WINDOW_DAYS days — never true
        for a document that is already expired (that's
        is_effectively_expired()'s own, mutually exclusive case)."""
        from datetime import timedelta

        from django.utils import timezone

        if document.status != DocumentStatus.VERIFIED or document.expiry_date is None:
            return False
        today = timezone.now().date()
        return today <= document.expiry_date <= today + timedelta(days=cls.EXPIRING_SOON_WINDOW_DAYS)
