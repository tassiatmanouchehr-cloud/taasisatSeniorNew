"""Future AI-verification extension point — Phase 1.1 (Manual Document
Verification).

`DocumentVerificationEvaluator` is a contract a future automated
evaluator could implement to pre-triage the review queue (e.g. sort by
confidence, flag likely fraud). No implementation of this Protocol exists
in this repository, and nothing in
`apps.accounts.services.verification_review_service.VerificationReviewService`
calls it — manual review remains the sole authoritative decision
mechanism. This module exists only so a future evaluator has a stable
shape to implement against, without requiring any change to the domain
model or the review service's transition rules.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class VerificationRecommendationOutcome(str, Enum):
    LIKELY_APPROVE = "likely_approve"
    LIKELY_REJECT = "likely_reject"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


@dataclass(frozen=True)
class VerificationRecommendation:
    outcome: VerificationRecommendationOutcome
    confidence: float
    notes: str = ""


class DocumentVerificationEvaluator(Protocol):
    """A future automated pre-triage step. Its output is advisory only —
    it must never be wired to set `VerificationDocument.status` directly;
    only `VerificationReviewService`'s reviewer-authorized methods do
    that."""

    def evaluate(self, document) -> VerificationRecommendation: ...
