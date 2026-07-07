"""
Match Orchestrator — Module 02 Matching Engine.

The single public entry point for running a matching pass over an Order.
Generates candidates via SupplierResolver, evaluates eligibility, ranks
eligible candidates, and persists MatchRound/MatchCandidate rows.

Matching only PROPOSES candidates:
- It never writes Order.assigned_supplier.
- It never calls Order.save() for assignment purposes.
- Actual assignment remains exclusively owned by
  apps.orders.services.status_machine.assign_supplier().

See docs/adr/ADR-002_MATCHING_ENGINE.md.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.kernel.services.event_publisher import EventPublisher
from apps.kernel.services.supplier_resolver import SupplierResolver
from apps.orders.models import Order

from ..models import MatchCandidate, MatchCandidateStatus, MatchRound, MatchRoundStatus
from .configuration import MatchingConfiguration
from .eligibility import EligibilityService
from .ranking import RankingService

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M02"


class MatchOrchestrator:
    """Orchestrates a single matching run for an Order."""

    @classmethod
    @transaction.atomic
    def run(cls, order_id, *, triggered_by=None) -> MatchRound:
        order = Order.objects.get(id=order_id)
        actor_id = getattr(triggered_by, "person_id", None)

        config_snapshot = {
            "max_candidates": MatchingConfiguration.get_max_candidates(tenant_id=order.tenant_id),
            "min_verification_level": MatchingConfiguration.get_minimum_verification_level(tenant_id=order.tenant_id),
            "ranking_weights": MatchingConfiguration.get_ranking_weights(tenant_id=order.tenant_id),
        }

        match_round = MatchRound.objects.create(
            tenant_id=order.tenant_id,
            order=order,
            status=MatchRoundStatus.RUNNING,
            triggered_by=triggered_by,
            config_snapshot=config_snapshot,
        )

        EventPublisher.publish(
            tenant_id=order.tenant_id,
            event_type="Matching.RunStarted.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=match_round.id,
            source_entity_type="MatchRound",
            payload={"order_id": str(order.id)},
            actor_id=actor_id,
        )

        try:
            candidate_suppliers = list(
                SupplierResolver.get_suppliers_for_matching(
                    tenant_id=order.tenant_id,
                    service_category_id=order.service_category_id,
                )
            )

            evaluations = [
                (supplier, EligibilityService.evaluate(order=order, supplier=supplier))
                for supplier in candidate_suppliers
            ]
            eligible_suppliers = [supplier for supplier, result in evaluations if result.eligible]

            ranked = RankingService.rank(order=order, candidates=eligible_suppliers)
            rank_lookup = {
                supplier.id: (position, score, breakdown)
                for position, (supplier, score, breakdown) in enumerate(ranked, start=1)
            }

            created_candidates = []
            for supplier, result in evaluations:
                position_info = rank_lookup.get(supplier.id)
                rank_position, rank_score, score_breakdown = position_info or (None, None, {})

                candidate = MatchCandidate.objects.create(
                    tenant_id=order.tenant_id,
                    match_round=match_round,
                    supplier=supplier,
                    eligible=result.eligible,
                    eligibility_code=result.code,
                    eligibility_reason=result.reason,
                    rank_score=rank_score,
                    score_breakdown=score_breakdown,
                    rank_position=rank_position,
                    status=MatchCandidateStatus.RANKED if result.eligible else MatchCandidateStatus.GENERATED,
                )
                created_candidates.append(candidate)

            match_round.status = MatchRoundStatus.COMPLETED
            match_round.completed_at = timezone.now()
            match_round.save(update_fields=["status", "completed_at"])

            EventPublisher.publish(
                tenant_id=order.tenant_id,
                event_type="Matching.RunCompleted.v1",
                source_module=SOURCE_MODULE,
                source_entity_id=match_round.id,
                source_entity_type="MatchRound",
                payload={
                    "order_id": str(order.id),
                    "candidate_count": len(created_candidates),
                    "eligible_count": len(eligible_suppliers),
                },
                actor_id=actor_id,
            )

            return match_round

        except Exception as exc:
            match_round.status = MatchRoundStatus.FAILED
            match_round.completed_at = timezone.now()
            match_round.failure_reason = str(exc)
            match_round.save(update_fields=["status", "completed_at", "failure_reason"])

            EventPublisher.publish(
                tenant_id=order.tenant_id,
                event_type="Matching.RunFailed.v1",
                source_module=SOURCE_MODULE,
                source_entity_id=match_round.id,
                source_entity_type="MatchRound",
                payload={"order_id": str(order.id), "error": str(exc)},
                actor_id=actor_id,
            )
            raise

    @classmethod
    def mark_candidate_selected(cls, *, match_candidate_id) -> MatchCandidate:
        """
        Mark a MatchCandidate as SELECTED after an assignment has already
        happened via orders.services.status_machine.assign_supplier().

        This method does not perform assignment — it only records, for
        audit/reporting, that a candidate previously proposed by matching
        was the one an external actor assigned. Callers are responsible
        for calling assign_supplier() themselves, before or independently
        of calling this method.
        """
        candidate = MatchCandidate.objects.get(id=match_candidate_id)
        candidate.status = MatchCandidateStatus.SELECTED
        candidate.save(update_fields=["status", "updated_at"])
        return candidate
